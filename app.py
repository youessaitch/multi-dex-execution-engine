import asyncio
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import redis.asyncio as aioredis
import time
import utils

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from utils import WS_CONNECTIONS, set_active_order_state, persist_order_to_db, update_order_in_db, log_order_message
from workers import Order, ORDER_QUEUE, process_order_worker, CONCURRENCY
from models import ExecuteOrderRequest

# -----------------------
# Config
# -----------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# -----------------------
# DB Setup
# -----------------------
engine = sa.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
metadata = sa.MetaData()

orders_table = sa.Table(
    "orders",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("token_in", sa.String),
    sa.Column("token_out", sa.String),
    sa.Column("amount", sa.Float),
    sa.Column("order_type", sa.String),
    sa.Column("status", sa.String),
    sa.Column("tx_hash", sa.String, nullable=True),
    sa.Column("executed_price", sa.Float, nullable=True),
    sa.Column("created_at", sa.Float, default=time.time),
    sa.Column("last_error", sa.String, nullable=True),
)

logs_table = sa.Table(
    "order_logs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("order_id", sa.String),
    sa.Column("level", sa.String),
    sa.Column("message", sa.String),
    sa.Column("ts", sa.Float, default=time.time),
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)

# Inject DB/Redis into utils
utils.redis = None
utils.Session = Session
utils.orders_table = orders_table
utils.logs_table = logs_table

# -----------------------
# FastAPI app
# -----------------------
app = FastAPI(title="Mock Order Execution Engine")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Startup
# -----------------------
@app.on_event("startup")
async def startup():
    utils.redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    for _ in range(CONCURRENCY):
        asyncio.create_task(process_order_worker())
    print("Startup complete. Workers running. Redis:", bool(utils.redis))

# -----------------------
# API Endpoints
# -----------------------


@app.post("/api/orders/execute")
async def submit_order(req: ExecuteOrderRequest):
    if req.order_type != "market":
        raise HTTPException(status_code=400, detail="Only 'market' supported in this demo")
    oid = str(uuid.uuid4())
    ord = Order(id=oid, token_in=req.token_in, token_out=req.token_out, amount=req.amount, order_type=req.order_type)
    persist_order_to_db(ord)
    await set_active_order_state(oid, {"status": "pending"})
    log_order_message(oid, "info", "Order submitted and queued")
    await ORDER_QUEUE.put(ord)
    return JSONResponse({"orderId": oid, "status": "pending", "message": "Open WebSocket /api/orders/execute?orderId=<id> to receive updates"})

@app.websocket("/api/orders/execute")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    oid = websocket.query_params.get("orderId")
    if not oid:
        await websocket.send_text('{"error": "Must provide orderId"}')
        await websocket.close()
        return
    WS_CONNECTIONS.setdefault(oid, set()).add(websocket)
    try:
        await websocket.send_text(f'{{"status": "connected", "orderId": "{oid}"}}')
        while True:
            try:
                msg = await websocket.receive_text()
                await websocket.send_text(f'{{"echo": "{msg}"}}')
            except WebSocketDisconnect:
                break
    finally:
        try:
            WS_CONNECTIONS[oid].remove(websocket)
        except KeyError:
            pass

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    s = Session()
    try:
        row = s.execute(orders_table.select().where(orders_table.c.id == order_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return dict(row._mapping)
    finally:
        s.close()

# Serve index.html
@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse("static/index.html")
