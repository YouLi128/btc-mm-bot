"""
Quote generation strategies.

Both strategies return (bid_price, ask_price) given the current
mid price and inventory.
"""

import datetime
from zoneinfo import ZoneInfo

_ET          = ZoneInfo("America/New_York")
_US_OPEN     = datetime.time(9, 30)
_US_CLOSE    = datetime.time(16, 0)
_SESSION_MIN = 390.0   # 09:30-16:00 = 6.5小时 = 390分钟


def us_session_tau() -> float:
    """
    τ 基于美股交易时段。

    盘中 (09:30-16:00 ET): τ 从 1.0 线性衰减到 0.0，越靠近收盘越紧迫。
    盘外: τ = 1.0，保守宽价差，不紧迫。

    原理：BTC 机构流量和波动率高度集中在美股交易时段，
    用 US session 作为"虚拟收盘"比随机重置 1440步 更有经济意义。
    """
    now = datetime.datetime.now(_ET)
    t   = now.time()

    if t < _US_OPEN or t >= _US_CLOSE:
        return 1.0

    open_min    = _US_OPEN.hour * 60 + _US_OPEN.minute
    now_min     = now.hour * 60 + now.minute + now.second / 60.0
    elapsed_min = now_min - open_min
    return max(1.0 - elapsed_min / _SESSION_MIN, 0.0)


class BaselineStrategy:
    """Fixed symmetric spread around mid."""

    def __init__(self, delta: float = 50.0):
        self.delta = delta

    def get_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
        return mid - self.delta, mid + self.delta


class ASStrategy:
    """
    Simplified Avellaneda-Stoikov，τ 对齐美股交易时段：
        r = mid - gamma * inventory * tau
        bid = r - delta(tau),  ask = r + delta(tau)

    When inventory > 0 (long): r < mid → ask cheaper → inventory sells down.
    When inventory < 0 (short): r > mid → bid dearer → inventory buys back.
    """

    def __init__(
        self,
        gamma: float = 50.0,
        delta_0: float = 45.0,
        delta_min: float = 5.0,
    ):
        self.gamma     = gamma
        self.delta_0   = delta_0
        self.delta_min = delta_min

    def get_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
        tau   = us_session_tau()
        r     = mid - self.gamma * inventory * tau
        delta = self.delta_0 * tau + self.delta_min
        return r - delta, r + delta

    def current_tau(self) -> float:
        return us_session_tau()
