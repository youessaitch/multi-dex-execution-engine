import asyncio
import random
from dataclasses import dataclass
import json
from utils import set_active_order_state, log_order_message, update_order_in_db, WS_CONNECTIONS
from models import MockDexRouter, Order

# -----------------------
# Concurrency
# -----------------------
CONCURRENCY = 10
ORDER_QUEUE: asyncio.Queue = asyncio.Queue()
semaphore = asyncio.Semaphore(CONCURRENCY)

# -----------------------
# Mock DEX Router
# -----------------------

dex_router = MockDexRouter()

# -----------------------
# Worker loop
# -----------------------
async def process_order_worker():
    while True:
        ord = await ORDER_QUEUE.get()
        try:
            # --- Pending ---
            ord.status = "pending"
            try:
                await set_active_order_state(ord.id, {"status": ord.status})
            except Exception as e:
                raise

            try:
                log_order_message(ord.id, "info", "Order is pending")
            except Exception as e:
                raise

            await notify_ws(order_id=ord.id, status=ord.status)
            await asyncio.sleep(0.5)

            # --- Routing ---
            ord.status = "routing"
            dex_prices = {
                "Raydium": round(ord.amount * (0.98 + random.random() * 0.04), 4),
                "Meteora": round(ord.amount * (0.97 + random.random() * 0.05), 4),
            }
            best_dex = min(dex_prices, key=dex_prices.get)
            best_price = dex_prices[best_dex]

            try:
                await set_active_order_state(ord.id, {
                    "status": ord.status,
                    "dex_prices": dex_prices
                })
            except Exception as e:
                raise

            try:
                log_order_message(ord.id, "info", f"Routing through DEXs: {dex_prices}, best={best_dex}")
            except Exception as e:
                raise

            await notify_ws(order_id=ord.id, status=ord.status,
                            extra={"dex_prices": dex_prices, "best_dex": best_dex})
            await asyncio.sleep(random.uniform(2, 3))

            # --- Building transaction ---
            ord.status = "building"
            try:
                await set_active_order_state(ord.id, {"status": ord.status})
            except Exception as e:
                raise

            try:
                log_order_message(ord.id, "info", "Building transaction")
            except Exception as e:
                raise

            await notify_ws(order_id=ord.id, status=ord.status)
            await asyncio.sleep(random.uniform(1, 2))

            # --- Submitted ---
            ord.status = "submitted"
            ord.tx_hash = f"0x{random.randint(10**15, 10**16 - 1):x}"
            ord.executed_price = best_price
            try:
                await set_active_order_state(ord.id, {
                    "status": ord.status,
                    "tx_hash": ord.tx_hash,
                    "executed_price": ord.executed_price
                })
            except Exception as e:
                raise

            try:
                log_order_message(ord.id, "info", f"Transaction submitted with tx_hash {ord.tx_hash}")
            except Exception as e:
                raise

            await notify_ws(order_id=ord.id, status=ord.status,
                            tx_hash=ord.tx_hash,
                            extra={"executedPrice": ord.executed_price, "best_dex": best_dex})
            await asyncio.sleep(random.uniform(2, 3))

            # --- Confirmed ---
            ord.status = "confirmed"
            try:
                update_order_in_db(ord)
            except Exception as e:
                raise

            try:
                log_order_message(ord.id, "info", "Transaction confirmed")
            except Exception as e:
                raise

            await notify_ws(order_id=ord.id, status=ord.status,
                            tx_hash=ord.tx_hash,
                            extra={"executedPrice": ord.executed_price, "best_dex": best_dex})

        except Exception as e:
            import traceback
            print(traceback.format_exc())

            ord.status = "failed"
            ord.last_error = str(e)

            try:
                await set_active_order_state(ord.id, {"status": ord.status, "error": ord.last_error})
            except Exception as e2:
                print(f"[ERROR] set_active_order_state (failed): {e2}")

            try:
                update_order_in_db(ord)
            except Exception as e2:
                print(f"[ERROR] update_order_in_db (failed): {e2}")

            try:
                log_order_message(ord.id, "error", f"Order failed: {e}")
            except Exception as e2:
                print(f"[ERROR] log_order_message (failed): {e2}")

            await notify_ws(order_id=ord.id, status=ord.status, error=str(e))


# -----------------------
# Helper function to make values JSON serializable
# -----------------------
def make_serializable(obj):
    """Recursively convert an object to be JSON serializable."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    else:
        return str(obj)

# -----------------------
# WebSocket notifier
# -----------------------
async def notify_ws(order_id, status, tx_hash=None, executed_price=None, error=None, extra=None):
    sockets = WS_CONNECTIONS.get(order_id, set())
    payload = {"status": status}

    if tx_hash is not None:
        payload["txHash"] = tx_hash
    if executed_price is not None:
        payload["executedPrice"] = executed_price
    if error is not None:
        payload["error"] = error

    if extra:
        payload["extra"] = make_serializable(extra)

    try:
        text_payload = json.dumps(payload)
    except (TypeError, OverflowError) as e:
        # Fallback: convert everything to strings
        safe_payload = {k: str(v) for k, v in payload.items()}
        text_payload = json.dumps(safe_payload)

    for ws in list(sockets):
        try:
            print(f"[DEBUG] WS Payload: {text_payload}")
            await ws.send_text(text_payload)
        except Exception:
            sockets.discard(ws)
            print(f"[ERROR] Failed to send WS message: {e}")
