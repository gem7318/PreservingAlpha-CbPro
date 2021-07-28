from __future__ import annotations

import math

from pydantic import BaseModel, Field


class Price(BaseModel):

    current: float = Field(default_factory=float)
    paid: float = Field(default_factory=float)
    sold: float = Field(default_factory=float)

    tolerance: float = Field(default_factory=float)
    hold_tolerance: float = Field(default_factory=float)

    upside_factor: float = Field(default_factory=float)
    downside_factor: float = Field(default_factory=float)

    currency: str = Field(default_factory=str)

    n: int = Field(default_factory=int)

    def __init__(self, **data):

        super().__init__(**data)

        self.tolerance = self.tolerance or 0.001
        self.upside_factor = self.upside_factor or 1
        self.hold_tolerance = self.tolerance * self.upside_factor
        self.downside_factor = self.downside_factor or 1

    @property
    def sell_target(self) -> int:
        """Sell at."""
        return math.ceil(self.paid * (1 + self.hold_tolerance))

    @property
    def buy_target(self) -> int:
        """Buy at."""
        return math.floor(
            self.sold * (1 - (self.tolerance * self.downside_factor))
        )

    def is_sellable(self) -> bool:
        """Sell asset based on price.paid and price.current."""
        return self.current >= self.sell_target

    def is_buyable(self) -> bool:
        """Buy asset based on price.sold and price.current."""
        return self.current <= self.buy_target

    def refresh(self) -> Price:
        """Re-set static attributes."""
        self.tolerance = self.tolerance or 0.001
        self.upside_factor = self.upside_factor or 1
        self.hold_tolerance = self.tolerance * self.upside_factor
        return self

    def _status_sell(self):
        """Returns sell-scenario console status."""
        current = f"current: ${int(self.current)}"
        paid = f"bought-at: ${int(self.paid)}"
        target = f"sell-target: ${self.sell_target}"
        current_vs_target = f"current-vs-target: ${int(self.current - self.sell_target)}"
        current_vs_paid = f"current-vs-bought: ${int(self.current - self.paid)}"
        return f"""
{self._status_prefix('selling')} {current}, {target}, {current_vs_target}, {paid}, {current_vs_paid}
        """.strip()

    def _status_buy(self) -> str:
        """Returns buy-scenario console status."""
        current = f"current: ${int(self.current)}"
        paid = f"sold-at: ${int(self.sold)}"
        target = f"buy-target: ${self.buy_target}"
        current_vs_target = f"current-vs-target: ${int(self.current - self.buy_target)}"
        current_vs_sold = f"current-vs-sold: ${int(self.current - self.sold)}"
        return f"""
{self._status_prefix('buying')} {current}, {target}, {current_vs_target}, {paid}, {current_vs_sold}
        """.strip()

    def _status_prefix(self, side: str):
        """Shared component of console output."""
        return f"""{self.tick} ({side}) {self.currency}"""

    def status(self, holding: bool):
        """Prints status to console."""
        if len(str(self.n)) >= 12:
            self.n = int()
        self.n += 1
        if holding:
            print(self._status_sell())
        else:
            print(self._status_buy())

    @property
    def tick(self) -> str:
        """Iteration number."""
        return str(self.n).zfill(12)
