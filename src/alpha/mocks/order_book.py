"""
Order book container for use in back-testing.
"""
from __future__ import annotations

import locale
from typing import List, Dict, Callable, Tuple, Union, Any, Optional
from datetime import datetime as dt

from src.alpha.number import Float
from src.alpha.order import Order
from src.alpha.static import md5_hash

# TODO: Add to src/alpha/mocks package


class OrderBook:
    """
    Mock order book.
    """
    
    def __init__(
        self,
        usd: Optional[Float] = None,
        amt: Optional[Float] = None,
    ):
        self.usd: Float = usd or Float()
        self.amt: Float = amt or Float()
        
        self.asset: str = str()
        self.orders: Dict[int, Order] = dict()
        self._id: int = int()

    def order(self, mode: str, price: Float, tm: int) -> Order:
        """Dummy order creation during back-testing."""
        order = (
            self._sell(price, tm) if mode == 'sell' else self._buy(price, tm)
        )
        self.orders[tm] = order
        if mode == 'buy':
            self.amt = self.amt + (self.usd / price)
            assert self.amt, f"{self.usd}, {price}"
            self.usd = Float()
        elif mode == 'sell':
            self.usd = self.usd + (self.amt * price)
            assert self.usd, f"{self.amt}, {price}"
            self.amt = Float()
        return order
        
    def _sell(self, price: Float, tm: int) -> Order:
        usd = self.usd + (self.amt * price)
        assert usd, f"{self.usd}, {self.amt}, {price}"
        return Order(
            id=md5_hash(f"{self._id}{str(tm)}"),
            model_id=str(self._id),
            created_at=dt.now(),
            done_at=dt.now(),
            side='sell',
            executed_value=usd,
            filled_size=self.amt,
            settled=True,
        )
        
    def _buy(self, price: Float, tm: int) -> Order:
        amt = self.amt + (self.usd / price)
        assert amt != 0, f"{self.usd}, {self.amt}, {price}"
        return Order(
            id=md5_hash(f"{self._id}{str(tm)}"),
            model_id=str(self._id),
            created_at=dt.now(),
            done_at=dt.now(),
            side='buy',
            funds=self.usd,
            specified_funds=self.usd,
            executed_value=self.usd,
            filled_size=amt,
            settled=True,
        )

    def __setattr__(self, key, value):
        vars(self)[key] = value

    def __setitem__(self, key, value):
        vars(self)[key] = value
