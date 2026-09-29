"""Run backend end-to-end checks in an owned disposable PostgreSQL container.

    venv/bin/python tools/ce_homebrew_check.py
    venv/bin/python tools/ce_homebrew_check.py --advanced
    venv/bin/python tools/ce_homebrew_check.py --guided

Requires Docker and the repository's existing test dependencies. Never reads the
application environment or a production database URL. Removes its own container
on success, failure or interrupt; preserves all pre-existing containers.
"""

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--advanced', action='store_true', help='Also verify atomic document editing and real Chromium studio journeys')
    parser.add_argument('--guided', action='store_true', help='Include Advanced plus Guided form authoring journeys')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    name = "ce-homebrew-check-" + uuid.uuid4().hex[:12]
    started = False
    try:
        subprocess.run(["docker", "run", "--rm", "-d", "--name", name,
            "-e", "POSTGRES_PASSWORD=ce_test", "-e", "POSTGRES_DB=ce_test",
            "-p", "127.0.0.1::5432", "postgres:16-alpine"], check=True, capture_output=True)
        started = True
        port_line = subprocess.check_output(["docker", "port", name, "5432/tcp"], text=True).strip()
        port = int(port_line.rsplit(":", 1)[1])
        deadline = time.monotonic() + 60
        while True:
            logs = subprocess.run(["docker", "logs", name], text=True, capture_output=True, check=True)
            ready = "PostgreSQL init process complete; ready for start up." in logs.stdout + logs.stderr
            try:
                if ready:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("The disposable PostgreSQL container did not become ready")
            time.sleep(0.5)
        env = {**os.environ, "CE_TEST_DATABASE_URL": f"postgresql://postgres:ce_test@127.0.0.1:{port}/ce_test"}
        tests = [
            "tests/creation_engine/test_ce_homebrew_runtime.py",
            "tests/creation_engine/test_ce_homebrew_backend.py"]
        if args.advanced or args.guided:
            tests += ["tests/creation_engine/test_ce_advanced.py", "tests/creation_engine/test_ce_advanced_browser.py"]
        if args.guided:
            tests += ["tests/creation_engine/test_ce_guided_homebrew.py"]
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=root, env=env)
        return result.returncode
    finally:
        if started:
            subprocess.run(["docker", "rm", "-f", name], check=True, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
