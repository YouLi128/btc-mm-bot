"""
WebSocket book ticker feed — streams real-time best bid/ask from Binance Testnet.

Stream: wss://testnet.binance.vision/ws/{symbol}@bookTicker
Message format: {"b": "best_bid", "a": "best_ask", "B": bid_qty, "A": ask_qty}
"""

import asyncio
import json
from typing import Callable, Optional

import websockets

TESTNET_WS = "wss://testnet.binance.vision/ws"


class BookTicker:
    def __init__(self, symbol: str):
        self.symbol    = symbol.lower()
        self.best_bid: Optional[float] = None
        self.best_ask: Optional[float] = None
        self._callbacks: list[Callable] = []

    def on_update(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    @property
    def mid(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2.0
        return None

    async def run(self) -> None:
        url = f"{TESTNET_WS}/{self.symbol}@bookTicker"
        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    print(f"[feed] connected to {url}")
                    async for raw in ws:
                        msg = json.loads(raw)
                        self.best_bid = float(msg["b"])
                        self.best_ask = float(msg["a"])
                        for cb in self._callbacks:
                            await cb(self.best_bid, self.best_ask)
            except Exception as e:
                print(f"[feed] disconnected ({e}), reconnecting in 3s…")
                await asyncio.sleep(3)
