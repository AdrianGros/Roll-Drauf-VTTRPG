"""Opt-in transports. No default engine/ruleset registrations or live cutover."""


def register(app, socketio):
    from .http import blueprint
    from . import authoring_http  # register authoring routes before blueprint installation
    from . import sheet_http  # versioned race-to-sheet adapter
    from . import homebrew_http  # private executable class/race/spell test adapter
    from . import advanced_http  # atomic power-user document editing
    from .sockets import register as register_sockets
    app.register_blueprint(blueprint, url_prefix="/api/ce")
    register_sockets(socketio)
