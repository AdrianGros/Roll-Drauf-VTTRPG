"""Bounded timer entry point for durable in-app reminders; no external delivery."""
import json


def main():
    from vtt import create_app
    from vtt.extensions import db
    from vtt.calendar_notes import process_due
    app=create_app('production')
    with app.app_context():
        try:
            print(json.dumps({'ready':process_due(limit=200)}),flush=True)
        finally:
            db.session.remove()


if __name__=='__main__':
    main()
