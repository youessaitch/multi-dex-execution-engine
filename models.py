from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel
import asyncio, random

@dataclass
class Order:
    id: str
    token_in: str
    token_out: str
    amount: float
    order_type: str = "market"
    status: str = "pending"
    tx_hash: Optional[str] = None
    executed_price: Optional[float] = None
    last_error: Optional[str] = None

class ExecuteOrderRequest(BaseModel):
    token_in: str
    token_out: str
    amount: float
    order_type: Optional[str] = "market"

class MockDexRouter:
    def __init__(self, base_price=1.0):
        self.base_price = base_price

    async def get_raydium_quote(self, token_in, token_out, amount):
        await asyncio.sleep(0.2 + random.random() * 0.2)
        price = self.base_price * (0.98 + random.random() * 0.04)
        fee = 0.003
        return {"dex": "Raydium", "price": price, "fee": fee}

    async def get_meteora_quote(self, token_in, token_out, amount):
        await asyncio.sleep(0.2 + random.random() * 0.25)
        price = self.base_price * (0.97 + random.random() * 0.05)
        fee = 0.002
        return {"dex": "Meteora", "price": price, "fee": fee}

    async def execute_swap(self, dex, order):
        await asyncio.sleep(2.0 + random.random() * 1.0)
        if random.random() < 0.08:
            raise Exception(f"Simulated {dex} execution error")
        tx_hash = "0x" + "".join(random.choice("0123456789abcdef") for _ in range(64))
        executed_price = self.base_price * (0.98 + random.random() * 0.05)
        return {"txHash": tx_hash, "executedPrice": executed_price}
