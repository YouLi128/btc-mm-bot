"""
Tracks cash, inventory, fills, and P&L in real time.
Writes every quote cycle and fill to a CSV log for post-session analysis.
"""

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class Fill:
    timestamp: datetime
    side: str
    price: float
    qty: float


class PositionTracker:
    def __init__(self, initial_cash: float, initial_inventory: float = 0.0,
                 log_path: str = "session_log.csv"):
        self.cash              = initial_cash
        self.inventory         = initial_inventory
        self._initial_cash     = initial_cash
        self.fills: List[Fill] = []
        self._start_time       = datetime.now(timezone.utc)

        # CSV log
        self._log_path = log_path
        self._csv_file = open(log_path, "w", newline="")
        self._writer   = csv.writer(self._csv_file)
        self._writer.writerow(["timestamp", "event", "mid", "bid", "ask",
                                "inventory", "mtm_pnl", "fill_side", "fill_price", "fill_qty"])

    # ------------------------------------------------------------------
    def record_fill(self, side: str, price: float, qty: float) -> None:
        if side == "BUY":
            self.cash      -= price * qty
            self.inventory += qty
        else:
            self.cash      += price * qty
            self.inventory -= qty

        f = Fill(datetime.now(timezone.utc), side, price, qty)
        self.fills.append(f)

        print(f"  [fill] {side:4s}  {qty:.4f} BTC @ ${price:,.2f}  "
              f"→ inventory={self.inventory:+.4f} BTC")

        self._writer.writerow([
            f.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "fill", "", "", "",
            f"{self.inventory:.6f}", "",
            side, f"{price:.2f}", f"{qty:.6f}",
        ])
        self._csv_file.flush()

    def log_quote(self, mid: float, bid: float, ask: float) -> None:
        self._writer.writerow([
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "quote", f"{mid:.2f}", f"{bid:.2f}", f"{ask:.2f}",
            f"{self.inventory:.6f}", f"{self.mtm_pnl(mid):.2f}",
            "", "", "",
        ])
        self._csv_file.flush()

    # ------------------------------------------------------------------
    def mtm_pnl(self, mid: float) -> float:
        return self.cash + self.inventory * mid - self._initial_cash

    def summary(self, mid: float) -> str:
        return (f"fills={len(self.fills):3d}  "
                f"inventory={self.inventory:+.4f} BTC  "
                f"MtM P&L=${self.mtm_pnl(mid):+,.2f}  "
                f"cash=${self.cash:,.2f}")

    def print_report(self, mid: float) -> None:
        buys  = [f for f in self.fills if f.side == "BUY"]
        sells = [f for f in self.fills if f.side == "SELL"]
        duration = datetime.now(timezone.utc) - self._start_time
        hours, rem = divmod(int(duration.total_seconds()), 3600)
        mins = rem // 60

        spread_pnl = sum(f.price * f.qty * (1 if f.side == "SELL" else -1)
                         for f in self.fills)

        print("\n" + "=" * 42)
        print("  Session Report")
        print("=" * 42)
        print(f"  Duration        : {hours}h {mins}min")
        print(f"  Total fills     : {len(self.fills)} ({len(buys)} buy / {len(sells)} sell)")
        print(f"  Final inventory : {self.inventory:+.4f} BTC")
        print(f"  Spread P&L      : ${spread_pnl:+,.2f}")
        print(f"  Inventory P&L   : ${self.mtm_pnl(mid) - spread_pnl:+,.2f}")
        print(f"  MtM P&L         : ${self.mtm_pnl(mid):+,.2f}")
        print(f"  Log saved       : {self._log_path}")
        print("=" * 42)

        self._csv_file.close()
