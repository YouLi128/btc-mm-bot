"""
Quote generation strategies.

Both strategies return (bid_price, ask_price) given the current
mid price and inventory.
"""


class BaselineStrategy:
    """Fixed symmetric spread around mid."""

    def __init__(self, delta: float = 50.0):
        self.delta = delta

    def get_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
        return mid - self.delta, mid + self.delta


class ASStrategy:
    """
    Simplified Avellaneda-Stoikov:
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
        session_steps: int = 1440,
    ):
        self.gamma         = gamma
        self.delta_0       = delta_0
        self.delta_min     = delta_min
        self.session_steps = session_steps
        self._step         = 0

    def reset(self) -> None:
        self._step = 0

    def get_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
        self._step += 1
        tau   = max(self.session_steps - self._step, 1) / self.session_steps
        r     = mid - self.gamma * inventory * tau
        delta = self.delta_0 * tau + self.delta_min
        return r - delta, r + delta
