"""Disposable PostgreSQL 16 for Creation Engine tests (G1 decision D4). Never touches the live database.

    python tools/ce_test_postgres.py start    # prints the export line for CE_TEST_DATABASE_URL
    python tools/ce_test_postgres.py stop

The container listens on 127.0.0.1 only and is removed when stopped. Tests
marked ``postgres`` are skipped unless CE_TEST_DATABASE_URL is set.
"""

import subprocess
import sys
import time

import psycopg2

NAME = "ce-test-postgres"
PORT = 55432
URL = f"postgresql://postgres:ce_test@127.0.0.1:{PORT}/ce_test"
READY = "PostgreSQL init process complete; ready for start up."


def start() -> None:
    started = subprocess.run(["docker", "run", "-d", "--rm", "--name", NAME, "-e", "POSTGRES_PASSWORD=ce_test",
                              "-e", "POSTGRES_DB=ce_test", "-p", f"127.0.0.1:{PORT}:5432", "postgres:16-alpine"],
                             capture_output=True, text=True)
    if started.returncode != 0:
        raise SystemExit(f"docker run failed: {started.stderr.strip()}")
    deadline = time.monotonic() + 90
    while True:
        result = subprocess.run(["docker", "logs", NAME], capture_output=True, text=True)
        logs = result.stdout + result.stderr      # the entrypoint prints its ready line to stdout
        if READY in logs:
            try:
                psycopg2.connect(URL).close()
                break
            except psycopg2.OperationalError:
                pass
        if time.monotonic() > deadline:
            raise SystemExit("disposable PostgreSQL did not become ready in 90 s")
        time.sleep(0.5)
    print(f"export CE_TEST_DATABASE_URL={URL}")


def stop() -> None:
    subprocess.run(["docker", "rm", "-f", NAME], check=True, capture_output=True)     # synchronous stop and removal


if __name__ == "__main__":
    {"start": start, "stop": stop}[sys.argv[1] if len(sys.argv) > 1 else "start"]()
