"""
Tracks cash, inventory, fills, and P&L in real time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Fill:
    timestamp: datetime
    side: str          # "BUY" | "SELL"
    price: float
    qty: float


class PositionTracker:
    def __init__(self, initial_cash: float, initial_inventory: float = 0.0):
        self.cash              = initial_cash
        self.inventory         = initial_inventory
        self._initial_cash     = initial_cash
        self._initial_inventory = initial_inventory
        self.fills: List[Fill] = []

    def record_fill(self, side: str, price: float, qty: float) -> None:
        if side == "BUY":
            self.cash      -= price * qty
            self.inventory += qty
        else:
            self.cash      += price * qty
            self.inventory -= qty
        self.fills.append(Fill(datetime.utcnow(), side, price, qty))
        print(f"  [fill] {side:4s}  {qty:.4f} BTC @ ${price:,.2f}  "
              f"→ inventory={self.inventory:+.4f} BTC")

    def mtm_pnl(self, mid: float) -> float:
        return self.cash + self.inventory * mid - self._initial_cash

    def spread_pnl(self) -> float:
        """Approximate realized spread gain: each fill earns half the spread."""
        total = 0.0
        for f in self.fills:
            total += f.price * f.qty if f.side == "SELL" else -f.price * f.qty
        return total

    def summary(self, mid: float) -> str:
        return (
            f"fills={len(self.fills):3d}  "
            f"inventory={self.inventory:+.4f} BTC  "
            f"MtM P&L=${self.mtm_pnl(mid):+,.2f}  "
            f"cash=${self.cash:,.2f}"
        )
