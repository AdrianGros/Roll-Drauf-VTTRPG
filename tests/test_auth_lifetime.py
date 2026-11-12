"""C03: absolute six-hour login limit, controlled by a fake clock (no real waiting).

Tokens that must exist "in the past" are minted directly with PyJWT; the
helper clock seam ``vtt.auth.lifetime._clock`` is moved instead of sleeping.
"""

import re
import secrets
import time

import jwt as pyjwt
import pytest
from flask_jwt_extended import decode_token

from vtt import create_app
from vtt.auth import lifetime
from vtt.auth.lifetime import (
    AuthLifetimeError,
    CLAIM_STARTED,
    CLAIM_UNTIL,
    check_payload,
    ts_to_naive,
)
from vtt.extensions import db, socketio
from vtt.models import DiscordIdentityLink, Role, Session, TableContext, User
from vtt.play import contexts
from vtt.utils.realtime import dm_room
from tests.play_shared import add_map, add_member, create_campaign, create_session

pytest_plugins = ["tests.play_shared"]

LIFE = 6 * 3600
PASSWORD = "SecurePass123!"


# --------------------------------------------------------------------- fixtures


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    app.config.update(
        DISCORD_LOGIN_ENABLED=True,
        DISCORD_CLIENT_ID="discord-client",
        DISCORD_CLIENT_SECRET="discord-secret",
        DISCORD_REDIRECT_URI="http://localhost/api/auth/discord/callback",
        DISCORD_GUILD_ID="1328724663257268264",
        DISCORD_BOT_VERIFICATION_URL="http://bot.local/vtt/discord/verify",
        DISCORD_BOT_SHARED_SECRET="shared-secret",
    )
    with app.app_context():
        db.create_all()
        for role_name in ["Player", "DM", "Admin"]:
            db.session.add(Role(name=role_name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    row = User(username="lifetime", email="lifetime@example.test", role_id=1)
    row.set_password(PASSWORD)
    db.session.add(row)
    db.session.commit()
    return row


class FakeClock:
    """Real time until ``at`` is called; afterwards fully controlled."""

    def __init__(self):
        self.value = None

    def now(self):
        return time.time() if self.value is None else self.value

    def at(self, ts):
        self.value = float(ts)


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(lifetime, "_clock", fake.now)
    return fake


def claims_of(token):
    """Signed claims without any time validation (clock is faked)."""
    return pyjwt.decode(token, options={"verify_signature": False})


def _is_deletion(header):
    return "Max-Age=0" in header or header.split(";", 1)[0].endswith("=")


def cookie_from(response, name):
    """The live (non-deleting) Set-Cookie for ``name``; legacy-path deletions are skipped."""
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(name + "=") and not _is_deletion(header):
            return header
    return None


def deletion_cookies(response, name):
    return [h for h in response.headers.getlist("Set-Cookie") if h.startswith(name + "=") and _is_deletion(h)]


def cookie_value(response, name):
    header = cookie_from(response, name)
    return header.split(";", 1)[0].split("=", 1)[1] if header else None


def max_age(header):
    return int(re.search(r"Max-Age=(\d+)", header).group(1))


def mint(app, user_id, token_type, *, started=None, until=None, exp=None, iat=None,
         jti=None, register=True, with_claims=True, **overrides):
    """Craft a signed token with explicit claims; optionally register its JTI."""
    base = int(time.time())
    started = base if started is None else started
    until = started + LIFE if until is None else until
    jti = jti or secrets.token_hex(8)
    payload = {
        "sub": str(user_id), "jti": jti, "type": token_type, "fresh": False,
        "iat": base if iat is None else iat, "nbf": base if iat is None else iat,
        "exp": exp if exp is not None else (started + 3600 if token_type == "access" else until),
    }
    if with_claims:
        payload[CLAIM_STARTED] = started
        payload[CLAIM_UNTIL] = until
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not ...}
    if register:
        db.session.add(Session(user_id=user_id, token_jti=jti,
                               expires_at=ts_to_naive(until if with_claims else payload["exp"])))
        db.session.commit()
    return pyjwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")


def payload_for(user_id, token_type="access", *, started=None, register=True, **overrides):
    """Decoded-payload dict for direct check_payload calls (+ registered row)."""
    now = int(time.time())
    started = now if started is None else started
    until = started + LIFE
    payload = {"sub": str(user_id), "jti": secrets.token_hex(8), "type": token_type,
               "iat": now, "exp": until, CLAIM_STARTED: started, CLAIM_UNTIL: until}
    payload.update(overrides)
    payload = {k: v for k, v in payload.items() if v is not ...}
    if register:
        db.session.add(Session(user_id=user_id, token_jti=payload["jti"], expires_at=ts_to_naive(until)))
        db.session.commit()
    return payload


def use_cookies(client, access=None, refresh=None):
    if access:
        client.set_cookie("access_token_cookie", access)
    if refresh:
        client.set_cookie("refresh_token_cookie", refresh)


# ------------------------------------------------------- issuing / login paths


def test_issue_tokens_sign_exact_window_and_register_both_jtis(app, user):
    with app.test_request_context():
        tokens = lifetime.issue_tokens(user.id)
    access, refresh = decode_token(tokens.access), decode_token(tokens.refresh)
    for payload in (access, refresh):
        assert payload[CLAIM_UNTIL] - payload[CLAIM_STARTED] == LIFE
        assert isinstance(payload[CLAIM_STARTED], int) and isinstance(payload[CLAIM_UNTIL], int)
    assert access["exp"] - access["iat"] <= 3600 + 1
    assert refresh["exp"] == refresh[CLAIM_UNTIL]
    rows = {row.token_jti: row for row in Session.query.filter_by(user_id=user.id)}
    assert set(rows) == {access["jti"], refresh["jti"]}
    assert all(row.expires_at == ts_to_naive(tokens.until) for row in rows.values())


def test_issue_tokens_never_exceed_absolute_end_and_anchor_is_kept(app, user, clock):
    started = int(time.time()) - LIFE + 600  # ten minutes left
    clock.at(time.time())
    with app.test_request_context():
        tokens = lifetime.issue_tokens(user.id, started=started, refresh=False)
    payload = claims_of(tokens.access)
    assert (payload[CLAIM_STARTED], payload[CLAIM_UNTIL]) == (started, started + LIFE)
    assert payload["exp"] <= started + LIFE
    assert payload["exp"] - payload["iat"] <= 601
    assert tokens.refresh is None
    with app.test_request_context(), pytest.raises(AuthLifetimeError):
        lifetime.issue_tokens(user.id, started=int(time.time()) - LIFE)


@pytest.mark.parametrize("remaining", [600, LIFE])
def test_exp_is_signed_from_the_integer_anchor_even_if_signing_clock_is_ahead(app, user, clock, remaining):
    """M1: helper clock one second behind the JWT library's clock must not push exp past until."""
    helper_now = int(time.time()) - 1  # library signs "iat" ~1s later than the helper's view
    clock.at(helper_now)
    started = helper_now - (LIFE - remaining)
    with app.test_request_context():
        tokens = lifetime.issue_tokens(user.id, started=started)
    until = started + LIFE
    access, refresh = claims_of(tokens.access), claims_of(tokens.refresh)
    assert refresh["exp"] == until
    assert access["exp"] == min(helper_now + 3600, until)  # exact, not relative to library time
    assert access["exp"] <= until
    assert check_payload(access, expected_type="access", now=helper_now).until == until


def _discord_login(client, app, monkeypatch, remember):
    user = User(username="disc", email="disc@example.test", role_id=1)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    db.session.add(DiscordIdentityLink(user_id=user.id, discord_user_id="423456789012345678"))
    db.session.commit()
    with client.session_transaction() as sess:
        sess["discord_oauth_state"] = "state-1"
        sess["discord_oauth_next"] = "/dashboard"
        sess["discord_remember_me"] = remember
        sess["discord_oauth_redirect_uri"] = "http://localhost/api/auth/discord/callback"
    monkeypatch.setattr("vtt.auth.routes.exchange_discord_code", lambda c, r: {"access_token": "d"})
    monkeypatch.setattr("vtt.auth.routes.fetch_discord_profile",
                        lambda t: {"id": "423456789012345678", "username": "disc", "email": "disc@example.test"})
    monkeypatch.setattr("vtt.auth.routes.verify_discord_with_bot",
                        lambda p: {"allowed": True, "role": "player", "guild_id": p["guild_id"]})
    response = client.get("/api/auth/discord/callback?code=c&state=state-1")
    assert response.status_code == 302
    return response, user.id


@pytest.mark.parametrize("path", ["register", "login", "login_remember", "discord", "discord_remember"])
def test_every_login_path_issues_bounded_registered_tokens(app, client, monkeypatch, path):
    if path == "register":
        response = client.post("/api/auth/register", json={
            "username": "newbie", "email": "newbie@example.com", "password": PASSWORD})
        assert response.status_code == 201
        user_id = User.query.filter_by(username="newbie").one().id
    elif path.startswith("login"):
        row = User(username="loginuser", email="loginuser@example.test", role_id=1)
        row.set_password(PASSWORD)
        db.session.add(row)
        db.session.commit()
        response = client.post("/api/auth/login", json={
            "username": "loginuser", "password": PASSWORD, "remember_me": path.endswith("remember")})
        assert response.status_code == 200
        user_id = row.id
    else:
        response, user_id = _discord_login(client, app, monkeypatch, path.endswith("remember"))

    access_header = cookie_from(response, "access_token_cookie")
    refresh_header = cookie_from(response, "refresh_token_cookie")
    access = claims_of(cookie_value(response, "access_token_cookie"))
    refresh = claims_of(cookie_value(response, "refresh_token_cookie"))
    assert access[CLAIM_STARTED] == refresh[CLAIM_STARTED]
    assert access[CLAIM_UNTIL] == refresh[CLAIM_UNTIL] == access[CLAIM_STARTED] + LIFE
    assert refresh["exp"] == refresh[CLAIM_UNTIL]  # remember-me does not extend
    assert access["exp"] <= access[CLAIM_UNTIL]
    for header in (access_header, refresh_header):
        assert LIFE - 5 <= max_age(header) <= LIFE
    rows = Session.query.filter_by(user_id=user_id).all()
    assert {row.token_jti for row in rows} == {access["jti"], refresh["jti"]}
    assert {row.expires_at for row in rows} == {ts_to_naive(access[CLAIM_UNTIL])}


# ----------------------------------------------------- access / refresh timing


def test_access_valid_at_59_minutes_and_expired_at_61(app, client, user, clock):
    started = int(time.time())
    use_cookies(client, access=mint(app, user.id, "access", started=started))
    clock.at(started + 59 * 60)
    assert client.get("/api/auth/me").status_code == 200
    clock.at(started + 61 * 60)
    assert client.get("/api/auth/me").status_code == 401


def test_refresh_before_and_after_absolute_end_keeps_anchor(app, client, user, clock):
    started = int(time.time())
    refresh = mint(app, user.id, "refresh", started=started)
    use_cookies(client, refresh=refresh)

    clock.at(started + LIFE - 30)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    new_access = claims_of(cookie_value(response, "access_token_cookie"))
    assert (new_access[CLAIM_STARTED], new_access[CLAIM_UNTIL]) == (started, started + LIFE)
    assert new_access["exp"] - new_access["iat"] <= 31  # remaining time, not one hour
    assert cookie_from(response, "refresh_token_cookie") is None  # same refresh token
    assert max_age(cookie_from(response, "access_token_cookie")) == 30

    clock.at(started + LIFE)
    assert client.post("/api/auth/refresh").status_code == 401
    clock.at(started + LIFE + 1)
    assert client.post("/api/auth/refresh").status_code == 401


def test_repeated_refresh_never_moves_the_anchor(app, client, user, clock):
    started = int(time.time())
    use_cookies(client, refresh=mint(app, user.id, "refresh", started=started))
    for offset in (10 * 60, 70 * 60, 3 * 3600, 5 * 3600 + 30 * 60):
        clock.at(started + offset)
        response = client.post("/api/auth/refresh")
        assert response.status_code == 200
        payload = claims_of(cookie_value(response, "access_token_cookie"))
        assert (payload[CLAIM_STARTED], payload[CLAIM_UNTIL]) == (started, started + LIFE)
        assert payload["exp"] <= started + LIFE
        assert Session.query.filter_by(token_jti=payload["jti"]).one().expires_at == ts_to_naive(started + LIFE)
    # 30 minutes left at the last refresh -> access bounded to it
    assert payload["exp"] - payload["iat"] <= 30 * 60 + 1


# --------------------------------------------------------------- legacy tokens


def test_legacy_access_drains_at_its_own_exp(app, client, user, clock):
    started = int(time.time())
    use_cookies(client, access=mint(app, user.id, "access", started=started, with_claims=False,
                                    exp=started + 3600, register=False))
    clock.at(started + 30 * 60)
    assert client.get("/api/auth/me").status_code == 200
    clock.at(started + 61 * 60)
    assert client.get("/api/auth/me").status_code == 401


def test_legacy_refresh_migrates_with_signed_iat_not_now(app, client, user, clock):
    now = int(time.time())
    iat = now - 3600
    legacy = mint(app, user.id, "refresh", with_claims=False, register=False, iat=iat, exp=now + 30 * 86400)
    use_cookies(client, refresh=legacy)
    clock.at(now)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    access = claims_of(cookie_value(response, "access_token_cookie"))
    refresh = claims_of(cookie_value(response, "refresh_token_cookie"))
    for payload in (access, refresh):
        assert (payload[CLAIM_STARTED], payload[CLAIM_UNTIL]) == (iat, iat + LIFE)
    assert refresh["exp"] == iat + LIFE  # remember-me's 30 days are gone
    assert LIFE - 3600 - 5 <= max_age(cookie_from(response, "refresh_token_cookie")) <= LIFE - 3600
    assert Session.query.filter_by(token_jti=refresh["jti"]).one().expires_at == ts_to_naive(iat + LIFE)


@pytest.mark.parametrize("case", ["too_old", "no_iat", "float_iat", "future_iat"])
def test_legacy_refresh_never_becomes_a_fresh_login(app, client, user, clock, case):
    now = int(time.time())
    clock.at(now)
    kwargs = {"with_claims": False, "register": False, "exp": now + 86400}
    if case == "too_old":
        kwargs["iat"] = now - LIFE - 1
    elif case == "no_iat":
        kwargs["iat"] = ...
    elif case == "float_iat":
        kwargs["iat"] = float(now - 100) + 0.5
    else:
        kwargs["iat"] = now + 3600
    token = mint(app, user.id, "refresh", **kwargs)
    use_cookies(client, refresh=token)
    assert client.post("/api/auth/refresh").status_code == 401
    assert Session.query.filter_by(user_id=user.id).count() == 0


def test_legacy_refresh_respects_user_logout_cutoff_including_same_second(app, client, user, clock):
    now = int(time.time())
    clock.at(now)
    iat = now - 100

    def logged_out_at(ts):
        for row in Session.query.filter_by(user_id=user.id):
            db.session.delete(row)
        db.session.add(Session(user_id=user.id, token_jti=secrets.token_hex(8),
                               expires_at=ts_to_naive(now + 3600), revoked_at=ts_to_naive(ts)))
        db.session.commit()

    legacy = mint(app, user.id, "refresh", with_claims=False, register=False, iat=iat, exp=now + 86400)
    use_cookies(client, refresh=legacy)
    logged_out_at(iat - 50)  # logout before this token existed: fine
    assert client.post("/api/auth/refresh").status_code == 200
    use_cookies(client, refresh=legacy)
    logged_out_at(iat + 50)  # logout after issue: revoked
    assert client.post("/api/auth/refresh").status_code == 401
    logged_out_at(iat)  # same second: fail closed for the unregistered legacy token
    assert client.post("/api/auth/refresh").status_code == 401


def test_new_login_in_same_second_as_logout_stays_valid_and_old_one_dies(app, client, user):
    first = client.post("/api/auth/login", json={"username": "lifetime", "password": PASSWORD})
    old_refresh = cookie_value(first, "refresh_token_cookie")
    assert client.post("/api/auth/logout").status_code == 200
    second_client = app.test_client()
    second = second_client.post("/api/auth/login", json={"username": "lifetime", "password": PASSWORD})
    assert second.status_code == 200
    # fresh login: its own registered, unrevoked JTI rows are authoritative
    assert second_client.post("/api/auth/refresh").status_code == 200
    assert second_client.get("/api/auth/me").status_code == 200
    stale = app.test_client()
    use_cookies(stale, refresh=old_refresh)
    assert stale.post("/api/auth/refresh").status_code == 401


# ----------------------------------------------------- strict claims / types


@pytest.mark.parametrize("name,overrides", [
    ("only_started", {CLAIM_UNTIL: ...}),
    ("only_until", {CLAIM_STARTED: ...}),
    ("string_started", {CLAIM_STARTED: "1"}),
    ("bool_until", {CLAIM_UNTIL: True}),
    ("float_started", {CLAIM_STARTED: 1.5}),
    ("window_too_long", {CLAIM_UNTIL: int(time.time()) + LIFE + 10}),
    ("window_too_short", {CLAIM_UNTIL: int(time.time()) + LIFE - 10}),
    ("started_in_future", {CLAIM_STARTED: int(time.time()) + 3600, CLAIM_UNTIL: int(time.time()) + 3600 + LIFE}),
    ("exp_after_until", {"exp": int(time.time()) + LIFE + 100}),
    ("missing_exp", {"exp": ...}),
    ("bad_sub", {"sub": "abc"}),
    ("empty_jti", {"jti": ""}),
    ("wrong_type_value", {"type": "magic"}),
])
def test_invalid_or_partial_claims_are_refused(app, user, name, overrides):
    payload = payload_for(user.id, register=False, **overrides)
    if isinstance(payload.get("jti"), str) and payload["jti"]:
        db.session.add(Session(user_id=user.id, token_jti=payload["jti"],
                               expires_at=ts_to_naive(int(time.time()) + LIFE)))
        db.session.commit()
    with pytest.raises(AuthLifetimeError):
        check_payload(payload)


def test_valid_payload_passes_and_registration_is_mandatory(app, user):
    assert check_payload(payload_for(user.id), expected_type="access").until is not None
    with pytest.raises(AuthLifetimeError, match="unregistered"):
        check_payload(payload_for(user.id, register=False))


def test_revoked_foreign_and_overlong_session_rows_are_refused(app, user):
    other = User(username="other", email="other@example.test", role_id=1)
    other.set_password(PASSWORD)
    db.session.add(other)
    db.session.commit()
    revoked = payload_for(user.id)
    Session.query.filter_by(token_jti=revoked["jti"]).one().revoked_at = ts_to_naive(time.time())
    foreign = payload_for(other.id)
    foreign["sub"] = str(user.id)
    overlong = payload_for(user.id)
    Session.query.filter_by(token_jti=overlong["jti"]).one().expires_at = ts_to_naive(time.time() + LIFE + 60)
    db.session.commit()
    for payload in (revoked, foreign, overlong):
        with pytest.raises(AuthLifetimeError):
            check_payload(payload)


def test_token_types_are_not_interchangeable(app, client, user):
    access = mint(app, user.id, "access")
    refresh = mint(app, user.id, "refresh")
    with pytest.raises(AuthLifetimeError, match="token_type"):
        check_payload(claims_of(refresh), expected_type="access")
    with pytest.raises(AuthLifetimeError, match="token_type"):
        check_payload(claims_of(access), expected_type="refresh")
    use_cookies(client, access=refresh, refresh=access)
    assert client.get("/api/auth/me").status_code in (401, 422)
    assert client.post("/api/auth/refresh").status_code in (401, 422)


def test_partial_claim_token_is_rejected_over_http(app, client, user):
    use_cookies(client, access=mint(app, user.id, "access", **{CLAIM_UNTIL: ...}))
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_both_new_jtis(app, client, user):
    login = client.post("/api/auth/login", json={"username": "lifetime", "password": PASSWORD})
    access = cookie_value(login, "access_token_cookie")
    assert client.post("/api/auth/logout").status_code == 200
    stale = app.test_client()
    use_cookies(stale, access=access)
    assert stale.get("/api/auth/me").status_code == 401
    assert all(row.revoked_at for row in Session.query.filter_by(user_id=user.id))


# --------------------------------------------------- socket / table boundary


def _join(socket, campaign, session, headers):
    socket.emit("session:join", {"campaign_id": campaign.id, "session_id": session.id,
                                "context_token": headers["X-VTT-Context"], "tab_id": headers["X-VTT-Tab"]})
    return socket.get_received()


def _enter(client, campaign, session, mode="dm"):
    tab = secrets.token_urlsafe(24)
    response = client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts",
                           json={"mode": mode, "tab": tab})
    assert response.status_code == 201, response.get_json()
    return {"X-VTT-Context": response.json["token"], "X-VTT-Tab": tab}


@pytest.fixture
def table(play_dm_user, play_player_user):
    campaign = create_campaign(play_dm_user, "Lifetime")
    add_member(campaign, play_player_user, "Player")
    session = create_session(campaign, status="in_progress", map_id=add_map(campaign, play_dm_user).id)
    return campaign, session


def _roll(socket, campaign, session):
    return socket.emit("roll_dice", {"campaign_id": campaign.id, "session_id": session.id, "dice": "1d20"},
                       callback=True)


def test_socket_parser_rejects_pure_decode_without_lifetime_check(app, user, clock):
    started = int(time.time())
    token = mint(app, user.id, "access", started=started)
    with app.test_request_context(headers={"Cookie": f"access_token_cookie={token}"}):
        from vtt.socket_handlers import _parse_authenticated_user
        assert _parse_authenticated_user()[1] is None
        clock.at(started + 61 * 60)  # access exp passed; no delegation exists
        assert _parse_authenticated_user()[0] is None
    refresh = mint(app, user.id, "refresh", started=started)
    clock.at(started)
    with app.test_request_context(headers={"Cookie": f"access_token_cookie={refresh}"}):
        assert _parse_authenticated_user()[0] is None  # refresh token as access


def test_delegation_survives_access_expiry_until_absolute_end(table, play_dm_client, play_dm_user, play_app, clock):
    campaign, session = table
    headers = _enter(play_dm_client, campaign, session)
    access = claims_of(play_dm_client.get_cookie("access_token_cookie").value)
    started, until = access[CLAIM_STARTED], access[CLAIM_UNTIL]
    context = TableContext.query.one()
    assert context.expires_at <= ts_to_naive(until)
    socket = socketio.test_client(play_app, flask_test_client=play_dm_client)
    try:
        assert any(e["name"] == "state:snapshot" for e in _join(socket, campaign, session, headers))
        # one hour later the access JWT is expired, the issuing login is not
        clock.at(started + 61 * 60)
        assert play_dm_client.get("/api/auth/me").status_code == 401
        result = _roll(socket, campaign, session)
        assert not (result and result.get("error") in {"unauthorized", "table_context_required"}), result
        assert contexts.validate(context)
        # refresh keeps the delegation usable (same issuing session row)
        assert play_dm_client.post("/api/auth/refresh").status_code == 200
        db.session.expire_all()
        assert contexts.validate(TableContext.query.one())
        result = _roll(socket, campaign, session)
        assert not (result and result.get("error") in {"unauthorized", "table_context_required"}), result
        # absolute end: input is refused and nothing is delivered any more
        clock.at(until + 1)
        result = _roll(socket, campaign, session)
        assert result and result.get("error") in {"unauthorized", "table_context_required"}
        socket.get_received()
        socketio.emit("test:private", {"secret": "after end"}, room=dm_room(campaign.id, session.id))
        assert not any(e["name"] == "test:private" for e in socket.get_received())
    finally:
        socket.disconnect()


def test_context_deadline_for_new_and_legacy_access_tokens(table, play_dm_client, play_dm_user, play_app, clock):
    campaign, session = table
    started = int(time.time())
    clock.at(started)
    capped = mint(play_app, play_dm_user.id, "access", started=started, exp=started + LIFE)
    play_dm_client.set_cookie("access_token_cookie", capped)
    _enter(play_dm_client, campaign, session)
    assert TableContext.query.order_by(TableContext.id.desc()).first().expires_at == ts_to_naive(started + LIFE)

    legacy = mint(play_app, play_dm_user.id, "access", with_claims=False, register=False,
                  started=started, exp=started + 1800)
    play_dm_client.set_cookie("access_token_cookie", legacy)
    _enter(play_dm_client, campaign, session, "player")
    assert TableContext.query.order_by(TableContext.id.desc()).first().expires_at == ts_to_naive(started + 1800)


def test_no_context_can_be_issued_after_absolute_end(table, play_dm_client, play_dm_user, play_app, clock):
    campaign, session = table
    started = int(time.time())
    play_dm_client.set_cookie("access_token_cookie",
                              mint(play_app, play_dm_user.id, "access", started=started, exp=started + LIFE))
    clock.at(started + LIFE + 1)
    response = play_dm_client.post(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts",
                                   json={"mode": "dm", "tab": secrets.token_urlsafe(24)})
    assert response.status_code in (401, 403)
    assert TableContext.query.count() == 0


def test_context_validate_honours_issuing_session_expiry_and_resume_keeps_identity(
        table, play_dm_client, play_app):
    campaign, session = table
    headers = _enter(play_dm_client, campaign, session, "player")
    context = TableContext.query.one()
    before = (context.id, context.mode, context.expires_at)
    receipt_free = TableContext.query.count()
    response = play_dm_client.post(
        f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/contexts", headers=headers,
        json={"resume": True, "mode": "dm", "tab": secrets.token_urlsafe(24)})
    assert response.status_code == 201 and response.json["mode"] == "player"
    db.session.expire_all()
    context = TableContext.query.one()
    assert (context.id, context.mode, context.expires_at) == before
    assert TableContext.query.count() == receipt_free
    # now the issuing login row lapses: the same context dies without owner fallback
    Session.query.filter_by(token_jti=context.auth_jti).one().expires_at = ts_to_naive(time.time() - 5)
    db.session.commit()
    assert not contexts.validate(context)
    new = {"X-VTT-Context": response.json["token"], "X-VTT-Tab": response.json["tab"]}
    result = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap", headers=new)
    assert result.status_code in (401, 403)
    result = play_dm_client.get(f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap")
    assert result.status_code in (401, 403)  # missing context never falls back to the owner


def test_outbound_delivery_checks_issuing_session_expiry(table, play_dm_client, play_app):
    campaign, session = table
    headers = _enter(play_dm_client, campaign, session, "dm")
    socket = socketio.test_client(play_app, flask_test_client=play_dm_client)
    try:
        _join(socket, campaign, session, headers)
        socketio.emit("test:private", {"secret": "before"}, room=dm_room(campaign.id, session.id))
        assert any(e["name"] == "test:private" for e in socket.get_received())
        context = TableContext.query.one()
        Session.query.filter_by(token_jti=context.auth_jti).one().expires_at = ts_to_naive(time.time() - 5)
        db.session.commit()
        socketio.emit("test:private", {"secret": "after"}, room=dm_room(campaign.id, session.id))
        received = socket.get_received()
        assert not any(e["name"] == "test:private" for e in received)
    finally:
        socket.disconnect()


# ------------------------------------------- M2: password change keeps current login

NEW_PASSWORD = "BrandNewPass456!"


def _real_login(app, username="lifetime"):
    """Login through the route; return (access, refresh, claims-of-access)."""
    response = app.test_client().post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    access, refresh = cookie_value(response, "access_token_cookie"), cookie_value(response, "refresh_token_cookie")
    return access, refresh, claims_of(access)


def _change_password(app, access, refresh=None):
    """Fresh client carrying the cookies on path '/' (the refresh cookie is
    path-scoped in browsers; here the contract with a *presented* cookie is tested)."""
    device = app.test_client()
    use_cookies(device, access=access, refresh=refresh)
    response = device.post("/api/auth/password/change",
                           json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    return device, response


def test_password_change_keeps_current_device_refresh_and_revokes_same_second_second_device(app, user, clock):
    access, refresh, claims = _real_login(app)
    started = claims[CLAIM_STARTED]
    # second device: same anchor => identical expires_at on its rows
    other_access = mint(app, user.id, "access", started=started)
    other_refresh = mint(app, user.id, "refresh", started=started)
    assert len({row.expires_at for row in Session.query.filter_by(user_id=user.id)}) == 1

    device, response = _change_password(app, access, refresh)
    assert response.status_code == 200
    assert device.get("/api/auth/me").status_code == 200

    other = app.test_client()
    use_cookies(other, access=other_access, refresh=other_refresh)
    assert other.get("/api/auth/me").status_code == 401
    assert other.post("/api/auth/refresh").status_code == 401

    # one hour later the current access has expired; the kept refresh still works
    clock.at(started + 61 * 60)
    assert device.get("/api/auth/me").status_code == 401
    refreshed = device.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    new_access = claims_of(cookie_value(refreshed, "access_token_cookie"))
    assert (new_access[CLAIM_STARTED], new_access[CLAIM_UNTIL]) == (started, started + LIFE)
    # ... but never beyond the original absolute end
    clock.at(started + LIFE)
    assert device.post("/api/auth/refresh").status_code == 401


@pytest.mark.parametrize("case", ["missing", "garbage", "bad_signature", "foreign_user", "other_anchor",
                                  "access_as_refresh", "revoked_row"])
def test_password_change_grants_no_exception_for_missing_or_invalid_refresh(app, user, case):
    access, refresh, claims = _real_login(app)
    started = claims[CLAIM_STARTED]
    other_user = User(username="stranger", email="stranger@example.test", role_id=1)
    other_user.set_password(PASSWORD)
    db.session.add(other_user)
    db.session.commit()
    if case == "missing":
        presented = None
    elif case == "garbage":
        presented = "not.a.jwt"
    elif case == "bad_signature":
        head, body, _ = refresh.split(".")
        presented = f"{head}.{body}.{'A' * 43}"
    elif case == "foreign_user":
        presented = mint(app, other_user.id, "refresh", started=started)
    elif case == "other_anchor":
        presented = mint(app, user.id, "refresh", started=started - 100)
    elif case == "access_as_refresh":
        presented = mint(app, user.id, "access", started=started)
    else:
        presented = mint(app, user.id, "refresh", started=started)
        Session.query.filter_by(token_jti=claims_of(presented)["jti"]).one().revoked_at = ts_to_naive(time.time())
        db.session.commit()

    device, response = _change_password(app, access, presented)
    assert response.status_code == 200
    assert device.get("/api/auth/me").status_code == 200  # current access is always kept
    # the real current refresh was not presented/valid here -> no shelter
    assert Session.query.filter_by(token_jti=claims_of(refresh)["jti"]).one().revoked_at is not None
    stale = app.test_client()
    use_cookies(stale, refresh=refresh)
    assert stale.post("/api/auth/refresh").status_code == 401
    if case in {"other_anchor", "access_as_refresh", "revoked_row"}:
        row = Session.query.filter_by(token_jti=claims_of(presented)["jti"]).one()
        assert row.revoked_at is not None
    if case == "foreign_user":
        # the stranger's login is never touched by someone else's password change
        assert Session.query.filter_by(user_id=other_user.id, revoked_at=None).count() == 1


def test_password_change_legacy_refresh_stays_bound_to_original_deadline(app, user, clock):
    now = int(time.time())
    clock.at(now)
    iat = now - 3600
    legacy_access = mint(app, user.id, "access", with_claims=False, register=False, iat=iat, exp=now + 1800)
    legacy_refresh = mint(app, user.id, "refresh", with_claims=False, register=False, iat=iat, exp=now + 30 * 86400)
    # another device: legacy login with a registered access row and its own refresh
    mint(app, user.id, "access", with_claims=False, iat=iat - 500, exp=now + 1000)
    other_refresh = mint(app, user.id, "refresh", with_claims=False, register=False, iat=iat - 500,
                         exp=now + 30 * 86400)

    device, response = _change_password(app, legacy_access, legacy_refresh)
    assert response.status_code == 200
    kept = Session.query.filter_by(token_jti=claims_of(legacy_refresh)["jti"]).one()
    assert kept.revoked_at is None
    assert kept.expires_at == ts_to_naive(iat + LIFE)  # original deadline, no new start

    other = app.test_client()
    use_cookies(other, refresh=other_refresh)
    assert other.post("/api/auth/refresh").status_code == 401  # legacy cutoff still hits other devices

    refreshed = device.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    payload = claims_of(cookie_value(refreshed, "access_token_cookie"))
    assert (payload[CLAIM_STARTED], payload[CLAIM_UNTIL]) == (iat, iat + LIFE)
    clock.at(iat + LIFE)
    assert device.post("/api/auth/refresh").status_code == 401


def test_password_change_rejects_legacy_refresh_from_another_login(app, user, clock):
    now = int(time.time())
    clock.at(now)
    legacy_access = mint(app, user.id, "access", with_claims=False, register=False, iat=now - 3600, exp=now + 1800)
    foreign_refresh = mint(app, user.id, "refresh", with_claims=False, register=False, iat=now - 7000,
                           exp=now + 86400)
    # the other login's registered legacy access row gives the revocation cutoff something to bite on
    mint(app, user.id, "access", with_claims=False, iat=now - 7000, exp=now + 900)
    _, response = _change_password(app, legacy_access, foreign_refresh)
    assert response.status_code == 200
    # a legacy refresh from a different login (iat too far from the access) is not adopted ...
    assert Session.query.filter_by(token_jti=claims_of(foreign_refresh)["jti"]).count() == 0
    stale = app.test_client()
    use_cookies(stale, refresh=foreign_refresh)
    # ... and is cut off by the logout/revocation cutoff
    assert stale.post("/api/auth/refresh").status_code == 401


def test_password_change_keeps_current_table_context(table, play_dm_client, play_dm_user, play_app):
    campaign, session = table
    headers = _enter(play_dm_client, campaign, session, "dm")
    context = TableContext.query.one()
    before = (context.id, context.mode, context.auth_jti, context.expires_at, context.revoked_at)
    response = play_dm_client.post("/api/auth/password/change",
                                   json={"current_password": "Password123!", "new_password": NEW_PASSWORD})
    assert response.status_code == 200
    db.session.expire_all()
    context = TableContext.query.one()
    assert (context.id, context.mode, context.auth_jti, context.expires_at, context.revoked_at) == before
    assert contexts.validate(context)
    base = f"/api/play/campaigns/{campaign.id}/sessions/{session.id}/bootstrap"
    assert play_dm_client.get(base, headers=headers).json["session_role"] == "DM"


def test_password_reset_and_logout_still_revoke_everything(app, client, user):
    access, refresh, claims = _real_login(app)
    device = app.test_client()
    use_cookies(device, access=access, refresh=refresh)
    assert device.post("/api/auth/logout").status_code == 200
    assert all(row.revoked_at for row in Session.query.filter_by(user_id=user.id))
    # reset path: _revoke_user_sessions without keep arguments revokes every row
    from vtt.auth.routes import _revoke_user_sessions
    access, refresh, claims = _real_login(app)
    _revoke_user_sessions(user.id)
    db.session.commit()
    assert all(row.revoked_at for row in Session.query.filter_by(user_id=user.id))


# ------------------------------------------------------ cookie path policy


def test_refresh_cookie_paths_and_legacy_deletions_on_login_and_logout(app, client, user):
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_CSRF_IN_COOKIES"] = True
    response = client.post("/api/auth/login", json={"username": "lifetime", "password": PASSWORD})
    assert response.status_code == 200
    refresh = cookie_from(response, "refresh_token_cookie")
    csrf = cookie_from(response, "csrf_refresh_token")
    assert "Path=/api/auth;" in refresh + ";" and "HttpOnly" in refresh
    assert "Path=/;" in csrf + ";" and "HttpOnly" not in csrf
    assert LIFE - 5 <= max_age(refresh) <= LIFE and LIFE - 5 <= max_age(csrf) <= LIFE
    # both pre-C03 cookies at /api/auth/refresh are expired explicitly
    for name in ("refresh_token_cookie", "csrf_refresh_token"):
        deletions = deletion_cookies(response, name)
        assert len(deletions) == 1 and "Path=/api/auth/refresh" in deletions[0]
    # the JWT itself never appears in the body
    assert cookie_value(response, "refresh_token_cookie") not in response.get_data(as_text=True)
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # logout itself is not under test for CSRF
    out = client.post("/api/auth/logout")
    for name in ("refresh_token_cookie", "csrf_refresh_token"):
        paths = " ".join(deletion_cookies(out, name))
        assert "Path=/api/auth/refresh" in paths


def test_register_and_discord_paths_use_the_same_cookie_policy(app, client, monkeypatch):
    response = client.post("/api/auth/register", json={
        "username": "pathy", "email": "pathy@example.com", "password": PASSWORD})
    assert response.status_code == 201
    assert "Path=/api/auth;" in cookie_from(response, "refresh_token_cookie") + ";"
    assert len(deletion_cookies(response, "refresh_token_cookie")) == 1
    discord, _ = _discord_login(app.test_client(), app, monkeypatch, False)
    assert "Path=/api/auth;" in cookie_from(discord, "refresh_token_cookie") + ";"
    assert len(deletion_cookies(discord, "csrf_refresh_token")) == 1


def test_legacy_migration_refresh_replaces_old_path_cookies(app, client, user, clock):
    now = int(time.time())
    clock.at(now)
    use_cookies(client, refresh=mint(app, user.id, "refresh", with_claims=False, register=False,
                                     iat=now - 60, exp=now + 86400))
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    assert "Path=/api/auth;" in cookie_from(response, "refresh_token_cookie") + ";"
    assert len(deletion_cookies(response, "refresh_token_cookie")) == 1
    # a plain new-style refresh only replaces the access cookie
    fresh = app.test_client()
    use_cookies(fresh, refresh=mint(app, user.id, "refresh", started=now))
    again = fresh.post("/api/auth/refresh")
    assert again.status_code == 200
    assert cookie_from(again, "refresh_token_cookie") is None
    assert deletion_cookies(again, "refresh_token_cookie") == []
