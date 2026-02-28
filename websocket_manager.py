import json
from typing import Dict
WS_CONNECTIONS: Dict[str, set] = {}

async def send_ws_message(order_id: str, payload: dict):
    payload_json = json.dumps(payload)
    sockets = WS_CONNECTIONS.get(order_id, set())
    for ws in list(sockets):
        try:
            await ws.send_text(payload_json)
        except Exception:
            try:
                sockets.remove(ws)
            except KeyError:
                pass
