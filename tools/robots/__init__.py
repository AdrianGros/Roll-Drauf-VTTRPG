"""Browser-automation robots for Roll Drauf VTT.

Modeled on the sister suite in goblin_delve_bot/tools/robots/ — same shape
(preflight -> stack -> accounts -> scenario -> report), adapted to this
project's stack: Flask + Flask-SocketIO + SQLAlchemy/Postgres, no Redis
needed for a single-process disposable run (SOCKETIO_MESSAGE_QUEUE stays
unset), schema created via AUTO_CREATE_SCHEMA rather than migration
replay.

    python -m tools.robots.run_all
"""
