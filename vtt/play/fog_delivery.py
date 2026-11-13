"""Private fog contents with a sequence position for every table connection."""
from vtt.extensions import socketio
from vtt.utils.realtime import build_event_envelope, sibling_envelope, session_room, user_room


def emit_private_fog(campaign_id, session_id, owner_id, fog):
    envelope = build_event_envelope(campaign_id, session_id, {"fog": fog.serialize()})
    # Owner first: its following duplicate tick is discarded by the client.
    socketio.emit("fog:updated", envelope, room=user_room(campaign_id, session_id, owner_id))
    socketio.emit("state:tick", sibling_envelope(envelope, {}), room=session_room(campaign_id, session_id))
