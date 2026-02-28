import json
import time
from typing import Dict, Optional

import redis.asyncio as aioredis

from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData
from db import Session, orders_table, logs_table

# -----------------------
# Config (should match app.py)
# -----------------------
DATABASE_URL = "sqlite:///./orders.db"  # override via env in app.py if needed
REDIS_URL = "redis://localhost:6379/0"
redis = None  # will be set in app.py startup
engine = create_engine(DATABASE_URL, echo=True, future=True) 
WS_CONNECTIONS: Dict[str, set] = {}  # will be shared

# -----------------------
# Helpers
# -----------------------
def make_redis_safe(value):
    """Ensure the value is a type Redis accepts."""
    if isinstance(value, (str, int, float)):
        return value
    return json.dumps(value)  # Serialize dicts/lists/complex types

async def set_active_order_state(order_id: str, mapping: dict):
    sanitized = {k: make_redis_safe(v) for k, v in mapping.items()}
    await redis.hset(f"order:{order_id}", mapping=sanitized)

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

def log_order_message(order_id: str, level: str, message: str):
    s = Session()
    try:
        s.execute(
            logs_table.insert().values(order_id=order_id, level=level, message=message, ts=time.time())
        )
        s.commit()
    finally:
        s.close()

def persist_order_to_db(ord):
    s = Session()
    try:
        s.execute(
            orders_table.insert().values(
                id=ord.id,
                token_in=ord.token_in,
                token_out=ord.token_out,
                amount=ord.amount,
                order_type=ord.order_type,
                status=ord.status,
                tx_hash=ord.tx_hash,
                executed_price=ord.executed_price,
                last_error=ord.last_error,
                created_at=time.time(),
            )
        )
        s.commit()
    finally:
        s.close()

def update_order_in_db(ord):
    s = Session()
    try:
        s.execute(
            orders_table.update()
            .where(orders_table.c.id == ord.id)
            .values(
                status=ord.status,
                tx_hash=ord.tx_hash,
                executed_price=ord.executed_price,
                last_error=ord.last_error,
            )
        )
        s.commit()
    finally:
        s.close()
