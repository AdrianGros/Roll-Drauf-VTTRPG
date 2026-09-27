"""Opt-in transports. No default engine/ruleset registrations or live cutover."""


def register(app, socketio):
    from .http import blueprint
    from . import authoring_http  # register authoring routes before blueprint installation
    from .sockets import register as register_sockets
    app.register_blueprint(blueprint, url_prefix="/api/ce")
    register_sockets(socketio)
