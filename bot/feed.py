"""
Book ticker feed via REST polling — Binance Testnet.

Binance testnet WebSocket is not reliably available on spot testnet,
so we poll the REST book ticker endpoint every second instead.
The quote loop only requotes every QUOTE_INTERVAL seconds, so 1-second
polling gives more than enough freshness.
"""

import asyncio
from typing import Optional, Callable

import requests

TESTNET_REST = "https://testnet.binance.vision"


class BookTicker:
    def __init__(self, symbol: str, poll_interval: float = 1.0):
        self.symbol        = symbol.upper()
        self.poll_interval = poll_interval
        self.best_bid: Optional[float] = None
        self.best_ask: Optional[float] = None
        self._callbacks: list[Callable] = []
        self._session = requests.Session()

    def on_update(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    @property
    def mid(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2.0
        return None

    async def run(self) -> None:
        url = f"{TESTNET_REST}/api/v3/ticker/bookTicker"
        print(f"[feed] polling {url} every {self.poll_interval}s")
        while True:
            try:
                resp = self._session.get(url, params={"symbol": self.symbol}, timeout=3)
                resp.raise_for_status()
                data = resp.json()
                self.best_bid = float(data["bidPrice"])
                self.best_ask = float(data["askPrice"])
                for cb in self._callbacks:
                    await cb(self.best_bid, self.best_ask)
            except Exception as e:
                print(f"[feed] error: {e}")
            await asyncio.sleep(self.poll_interval)
