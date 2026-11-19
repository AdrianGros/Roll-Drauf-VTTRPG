#!/usr/bin/env python3
"""Mark due private reminders ready; run --once from an existing host timer.

No push, email or Discord side effects. DB rows are authoritative and retries are safe.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=60)
    parser.add_argument('--limit', type=int, default=200)
    parser.add_argument('--config', choices=['production', 'testing'], default='production')
    args = parser.parse_args()
    if not 10 <= args.interval <= 3600 or not 1 <= args.limit <= 500:
        parser.error('interval must be 10–3600 seconds and limit 1–500')
    from vtt import create_app
    from vtt.calendar_notes import process_due
    from vtt.extensions import db
    app = create_app(args.config)
    while True:
        with app.app_context():
            try:
                print(json.dumps({'ready': process_due(args.limit)}), flush=True)
            finally:
                db.session.remove()
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
