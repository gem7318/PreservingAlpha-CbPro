"""
Unpacked ticker response.
"""
from __future__ import annotations

from typing import Optional, Dict, ContextManager
from contextlib import contextmanager

from pydantic import Field

from .base import Alpha
from .mocks.number import Float

import datetime as dt


class Tick(Alpha):
    """
    A single ticker response for a bid or an offer.
    """

    # -- From Ticker --
    type: str = Field(default_factory=str)
    sequence: int = Field(default_factory=int)
    asset_id: str = Field(default_factory=str, alias="product_id")
    price: Float = Field(default_factory=Float)
    open_24h: Float = Field(default_factory=Float)
    volume_24h: Float = Field(default_factory=Float)
    high_24h: Float = Field(default_factory=Float)
    low_24h: Float = Field(default_factory=Float)
    volume_30d: Float = Field(default_factory=Float)
    best_bid: Float = Field(default_factory=Float)
    best_ask: Float = Field(default_factory=Float)
    side: str = Field(default_factory=str)
    time: dt.datetime = Field(default_factory=dt.datetime.now)
    trade_id: int = Field(default_factory=int)
    last_size: Float = Field(default_factory=Float)

    def __getitem__(self, item):
        """Getter for class."""
        return vars(self)[item]


class Ticker(Alpha):
    """
    A complete ticker message (bid + offer).
    """
    
    def __init__(
        self,
        buy: Optional[Dict, Tick] = None,
        sell: Optional[Dict, Tick] = None,
        sleep: Optional[int] = None,
        **data
    ):
        
        super().__init__(asset=data.get('product_id'), **data)
        
        #: Tick: Bid / buy side
        self.buy: Tick = Tick(**buy) if buy else None
        
        #: Tick: Offer / sell side
        self.sell: Tick = Tick(**sell) if sell else None
        
        #: datetime: Timestamp on last ticker message received
        self.time: dt.datetime = (
            None
            if not self.buy or self.sell
            else max(self.buy.time, self.sell.time)
        )
        self.doc_fields['time'] = False
        
        #: int: Insert no more than 1 message per sleep seconds
        self.sleep: int = sleep or 1
        self.doc_fields['sleep'] = False
        
        self.id_field = 'time'
        self.mongo.db.name = 'ticker'
        
        super().__post__init__(**data)
        
    def msg(self, msg: Dict) -> Ticker:
        """Process raw ticker response.

        Args:
            msg (Dict):
                A raw ticker message.
        """
        msg['time'] = self.iso_to_dt(msg['time'])
        tick = Tick(**msg)
        if tick.side == 'sell':
            self.sell = tick
        else:
            self.buy = tick
        return self
    
    def tm(
        self, last: bool = False, current: bool = False
    ) -> dt.datetime:
        """Get last message timestamp or max timestamp of bid/offer messages."""
        if last:
            return self.time
        if current:
            if self.buy and self.sell:
                return max(self.buy.time, self.sell.time)
            elif self.buy:
                return self.buy.time
            else:
                return self.sell.time
    
    @contextmanager
    def clear(self) -> ContextManager[Ticker]:
        """Clear buy/sell attributes upon exit of context."""
        try:
            if self.buy and self.sell:
                self.time = self.field_id = max(self.buy.time, self.sell.time)
            yield
        finally:
            if self.response.inserted_id:
                self.response, self.buy, self.sell = None, None, None
    
    def insert(
        self,
        **kwargs
    ) -> Ticker:
        """Custom insert method for Ticker to record timing."""
        with self.clear():
            super().insert(**kwargs)
        return self
    
    def __bool__(self):
        """Evaluates to 'True' if the bid and the offer have been populated."""
        if not (self.sell and self.buy):
            return False
        if not self.time:
            return True
        return (
            (self.tm(current=True) - self.tm(last=True)).seconds
            > self.sleep
        )
