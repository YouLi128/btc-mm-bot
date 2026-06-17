"""
Binance Testnet REST client.
All requests are HMAC-SHA256 signed.

Testnet base URL: https://testnet.binance.vision
Get API keys at:  https://testnet.binance.vision  (log in with GitHub)
"""

import hashlib
import hmac
import time
from typing import Optional

import requests

_NETWORK_EXC = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
_RETRY_DELAYS = (3, 10, 30)   # 断网后第1、2、3次重试等待秒数

BASE_URL = "https://testnet.binance.vision"


class BinanceTestnet:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key    = api_key
        self.api_secret = api_secret.encode()
        self._session   = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": api_key})

    # ------------------------------------------------------------------
    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        sig   = hmac.new(self.api_secret, query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _get(self, path: str, params: dict = None) -> dict:
        last_exc: Exception = RuntimeError("no attempt made")
        for i, delay in enumerate((0, *_RETRY_DELAYS)):
            if delay:
                print(f"  [net] GET {path} retry {i}/{len(_RETRY_DELAYS)} in {delay}s…")
                time.sleep(delay)
            try:
                r = self._session.get(
                    f"{BASE_URL}{path}",
                    params=self._sign(dict(params or {})),
                    timeout=10,
                )
                r.raise_for_status()
                return r.json()
            except _NETWORK_EXC as e:
                last_exc = e
                print(f"  [net] {e.__class__.__name__}: {e}")
        raise last_exc

    def _post(self, path: str, params: dict) -> dict:
        last_exc: Exception = RuntimeError("no attempt made")
        for i, delay in enumerate((0, *_RETRY_DELAYS)):
            if delay:
                print(f"  [net] POST {path} retry {i}/{len(_RETRY_DELAYS)} in {delay}s…")
                time.sleep(delay)
            try:
                r = self._session.post(
                    f"{BASE_URL}{path}",
                    params=self._sign(dict(params)),
                    timeout=10,
                )
                r.raise_for_status()
                return r.json()
            except _NETWORK_EXC as e:
                last_exc = e
                print(f"  [net] {e.__class__.__name__}: {e}")
        raise last_exc

    def _delete(self, path: str, params: dict) -> dict:
        last_exc: Exception = RuntimeError("no attempt made")
        for i, delay in enumerate((0, *_RETRY_DELAYS)):
            if delay:
                print(f"  [net] DELETE {path} retry {i}/{len(_RETRY_DELAYS)} in {delay}s…")
                time.sleep(delay)
            try:
                r = self._session.delete(
                    f"{BASE_URL}{path}",
                    params=self._sign(dict(params)),
                    timeout=10,
                )
                r.raise_for_status()
                return r.json()
            except _NETWORK_EXC as e:
                last_exc = e
                print(f"  [net] {e.__class__.__name__}: {e}")
        raise last_exc

    # ------------------------------------------------------------------
    def get_account(self) -> dict:
        return self._get("/api/v3/account")

    def get_balances(self) -> dict:
        """Returns {asset: free_amount} for non-zero balances."""
        data = self.get_account()
        return {b["asset"]: float(b["free"])
                for b in data["balances"] if float(b["free"]) > 0}

    def place_limit_order(
        self,
        symbol: str,
        side: str,        # "BUY" or "SELL"
        price: float,
        quantity: float,
    ) -> dict:
        return self._post("/api/v3/order", {
            "symbol":      symbol,
            "side":        side,
            "type":        "LIMIT",
            "timeInForce": "GTC",
            "price":       f"{price:.2f}",
            "quantity":    f"{quantity:.4f}",
        })

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        try:
            return self._delete("/api/v3/order", {"symbol": symbol, "orderId": order_id})
        except requests.HTTPError:
            return {}   # already filled or cancelled — safe to ignore

    def cancel_all_orders(self, symbol: str) -> list:
        try:
            return self._delete("/api/v3/openOrders", {"symbol": symbol})
        except requests.HTTPError:
            return []

    def get_open_orders(self, symbol: str) -> list:
        return self._get("/api/v3/openOrders", {"symbol": symbol})

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._get("/api/v3/order", {"symbol": symbol, "orderId": order_id})
