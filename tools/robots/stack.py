"""The disposable VTT server the robots play against.

A throwaway Postgres cluster plus this repo's own Flask/SocketIO process,
both torn down when the run ends. Nothing here may touch the live
database or the live Redis instance: the robots register real accounts,
create real campaigns and roll real dice, and doing that against the
players' shared world would be indistinguishable from vandalism (see
goblin_delve_bot's own 2026-08-11 incident, the reason this check exists
at all in the sister suite this one is modeled on).

Deliberately simpler than the Goblin Delve stack in two ways:
  * No Redis. SOCKETIO_MESSAGE_QUEUE is only read from REDIS_URL
    (vtt/config.py DevelopmentConfig) -- leaving REDIS_URL unset gives a
    single-process Socket.IO server, exactly right for one robot run.
  * No migration replay. AUTO_CREATE_SCHEMA=True (the Development/Testing
    config default) makes vtt/__init__.py call db.create_all() straight
    from the current models on first request -- there is no Alembic
    versions/ directory in this repo to replay (confirmed 2026-08-22;
    the flask db upgrade references in infra/scripts and migrations/
    README.md are aspirational, not the real bootstrap path).
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENV_PYTHON = REPO / "venv" / "bin" / "python"
POSTGRES_USER = "postgres"


class StackError(RuntimeError):
    pass


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _live_database_url() -> str:
    """Best-effort read of whatever DATABASE_URL the live deployment
    uses, from the env files docker-compose.live.yml references -- so
    the same refusal check the sister suite has can compare against it."""
    for name in (".env.vtt.roll-drauf.de", ".env"):
        candidate = REPO / name
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return ""


def _refuse_live_database(url: str) -> None:
    """The one check that must never be removed -- see module docstring."""
    live = _live_database_url()
    if live and url.strip() == live.strip():
        raise StackError(
            "REFUSING TO RUN: the robots were pointed at the live "
            "database. They register real accounts and create real "
            "campaigns. Use a throwaway cluster.")


@dataclass
class Stack:
    base_url: str
    database_url: str
    data_dir: Path
    _postgres_port: int
    _app: subprocess.Popen
    _log: Path

    def app_log(self) -> str:
        try:
            return self._log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""


@contextlib.contextmanager
def disposable_stack(workdir: Path):
    """Bring up Postgres + the Flask/SocketIO app, yield a Stack, tear
    both down."""
    workdir.mkdir(parents=True, exist_ok=True)
    # mkdtemp creates a 0700 parent.  PostgreSQL needs to traverse this exact
    # throwaway directory, while the app still owns its own files within it.
    workdir.chmod(0o711)
    data_dir = workdir / "pgdata"
    socket_dir = workdir / "pgsock"
    data_dir.mkdir(exist_ok=True)
    socket_dir.mkdir(exist_ok=True)
    postgres_log = workdir / "postgres.log"
    postgres_log.touch()
    pg_port = _free_port()
    app_port = _free_port()

    for postgres_path in (data_dir, socket_dir, postgres_log):
        _grant_postgres_access(postgres_path)

    _run_as_postgres(["initdb", "-D", str(data_dir), "-A", "trust",
                      "-U", "postgres"])
    _run_as_postgres([
        "pg_ctl", "-D", str(data_dir), "-l", str(postgres_log),
        "-o", f"-p {pg_port} -k {socket_dir}", "start"])
    app_process = None
    try:
        _wait_for_postgres(pg_port)
        _run_as_postgres(["psql", "-h", str(socket_dir), "-p", str(pg_port),
                          "-U", "postgres", "-c", "CREATE DATABASE robots"])
        database_url = f"postgresql://postgres@127.0.0.1:{pg_port}/robots"
        _refuse_live_database(database_url)

        log_path = workdir / "app.log"
        env = _app_environment(database_url, app_port, storage_path=workdir / "assets")
        with log_path.open("w", encoding="utf-8") as log_file:
            app_process = subprocess.Popen(
                [str(VENV_PYTHON), str(REPO / "app.py")],
                cwd=REPO, env=env, stdout=log_file, stderr=subprocess.STDOUT)
            base_url = f"http://127.0.0.1:{app_port}"
            _wait_for_app(base_url, app_process, log_path)
            yield Stack(base_url=base_url, database_url=database_url,
                        data_dir=data_dir, _postgres_port=pg_port,
                        _app=app_process, _log=log_path)
    finally:
        if app_process is not None and app_process.poll() is None:
            app_process.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                app_process.wait(timeout=15)
        _run_as_postgres(["pg_ctl", "-D", str(data_dir), "-m", "immediate",
                          "stop"], check=False)


def _app_environment(database_url: str, app_port: int, *, storage_path: Path | None = None) -> dict:
    env = dict(os.environ)
    # Staging keeps the development database bootstrap but disables the
    # development SQL echo.  Robot logs are evidence, not a SQL transcript.
    env["FLASK_ENV"] = "staging"
    env["DATABASE_URL"] = database_url
    # Fresh, throwaway secrets per run -- never the insecure dev defaults
    # vtt/config.py ships (those would trip _validate_production_config
    # if this ever ran with ENV=production, and are simply bad hygiene
    # for anything that mints real JWTs, even disposable ones).
    env["SECRET_KEY"] = secrets.token_urlsafe(32)
    env["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    env["HOST"] = "127.0.0.1"
    env["PORT"] = str(app_port)
    env["FLASK_DEBUG"] = "0"
    # Deliberately unset: REDIS_URL, SOCKETIO_MESSAGE_QUEUE -- single
    # process, no pub/sub needed for one robot run (see module docstring).
    env.pop("REDIS_URL", None)
    env.pop("SOCKETIO_MESSAGE_QUEUE", None)
    # Discord OAuth off: robots never walk through Discord, and leaving
    # it enabled would redirect /register and /signup away from the real
    # local-password registration form the robots use instead.
    env["DISCORD_LOGIN_ENABLED"] = "false"
    env["RATELIMIT_STORAGE_URL"] = "memory://"
    # The local stack deliberately repeats the same authenticated journey
    # across the browser matrix; production rate limits must not turn later
    # matrix cells into 429/login failures.
    env["RATELIMIT_ENABLED"] = "false"
    env["LOCAL_STORAGE_PATH"] = str(storage_path or Path("/tmp/vtt-assets"))
    env["CORS_ORIGINS"] = f"http://127.0.0.1:{app_port}"
    env["PYTHONPATH"] = str(REPO)
    return env


def _run_as_postgres(argv: list[str], *, check: bool = True) -> None:
    binary = shutil.which(argv[0]) or f"/usr/bin/{argv[0]}"
    sudo = shutil.which("sudo")
    if sudo and os.geteuid() != 0:
        result = subprocess.run(
            [sudo, "-n", "-u", POSTGRES_USER, binary, *argv[1:]],
            capture_output=True, text=True,
        )
    else:
        quoted = " ".join(_shell_quote(part) for part in [binary, *argv[1:]])
        result = subprocess.run(["su", POSTGRES_USER, "-c", quoted],
                                capture_output=True, text=True)
    if check and result.returncode != 0:
        raise StackError(f"{argv[0]} failed: {result.stderr.strip()}")


def _grant_postgres_access(workdir: Path) -> None:
    """Make only this newly-created disposable stack usable by postgres.

    CI and the local developer shell may run as an unprivileged user.  The
    previous direct ``chown`` worked only when the whole robot process ran as
    root, which made the disposable stack fail before any browser test could
    start.  Prefer the direct operation, then use non-interactive sudo for
    this exact temp path when policy allows it.
    """
    command = ["chown", "-R", POSTGRES_USER, str(workdir)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        sudo = shutil.which("sudo")
        if not sudo or os.geteuid() == 0:
            raise
        subprocess.run([sudo, "-n", *command], check=True,
                       capture_output=True, text=True)


def _shell_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\\''") + "'"


def _wait_for_postgres(port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with contextlib.suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        time.sleep(0.2)
    raise StackError("Postgres did not come up")


def _wait_for_app(base_url: str, process: subprocess.Popen,
                  log_path: Path, timeout: float = 90.0) -> None:
    import httpx
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise StackError(
                "the app died during startup:\n"
                + log_path.read_text(encoding="utf-8", errors="replace")[-3000:])
        with contextlib.suppress(Exception):
            response = httpx.get(f"{base_url}/health/live", timeout=2)
            if response.status_code < 500:
                return
        time.sleep(0.5)
    raise StackError("the app never became reachable on /health/live")
