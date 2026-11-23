"""The hub advertises scheduled/ready starts, within the existing DM boundary."""
import pytest

from tests.play_shared import create_campaign, create_session, enter_table
from vtt.extensions import db
from vtt.models import SessionState

pytest_plugins = ['tests.play_shared']


@pytest.mark.parametrize('status', ['scheduled', 'ready', 'in_progress', 'paused', 'ended', 'cancelled'])
def test_start_accepts_only_unstarted_statuses(play_dm_client, play_dm_user, status):
    campaign = create_campaign(play_dm_user)
    session = create_session(campaign, status=status)
    enter_table(play_dm_client, campaign, session, 'dm')
    response = play_dm_client.post(f'/api/campaigns/{campaign.id}/sessions/{session.id}/start')
    allowed = status in {'scheduled', 'ready'}
    assert response.status_code == (200 if allowed else 409), response.get_json()
    db.session.refresh(session)
    assert session.status == ('in_progress' if allowed else status)
    assert (session.started_at is not None) == allowed
    if allowed:
        state = SessionState.query.filter_by(game_session_id=session.id).one()
        assert state.state_status == 'live'


def test_ready_start_cannot_bypass_owner_player_context(play_dm_client, play_dm_user):
    campaign = create_campaign(play_dm_user)
    session = create_session(campaign, status='ready')
    enter_table(play_dm_client, campaign, session, 'player')
    response = play_dm_client.post(f'/api/campaigns/{campaign.id}/sessions/{session.id}/start')
    assert response.status_code == 403
    db.session.refresh(session)
    assert session.status == 'ready' and session.started_at is None


def test_ready_start_keeps_other_running_session_conflict(play_dm_client, play_dm_user):
    campaign = create_campaign(play_dm_user)
    running = create_session(campaign, 'Already running', status='in_progress')
    target = create_session(campaign, 'Prepared next session', status='ready')
    enter_table(play_dm_client, campaign, target, 'dm')
    response = play_dm_client.post(f'/api/campaigns/{campaign.id}/sessions/{target.id}/start')
    assert response.status_code == 409
    assert response.json['error'] == 'another session is already in progress'
    db.session.refresh(target)
    db.session.refresh(running)
    assert target.status == 'ready' and running.status == 'in_progress'
