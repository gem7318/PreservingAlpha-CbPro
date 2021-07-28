"""
Unpacked order as returned by cb.get_orders().
"""
from __future__ import annotations

import json

from pydantic import Field
from datetime import datetime

from .base import Alpha
from .mocks.number import Float
from .sms import SMS
from .msg import Msg


class Order(Alpha):
    """
    Order object as returned by cb.get_orders() method.
    """
    oid: str = Field(default_factory=str, alias="id")
    model_id: str = Field(default_factory=str)
    created_at: datetime = Field(default_factory=str)
    product_id: str = Field(default_factory=str)
    profile_id: str = Field(default_factory=str)
    side: str = Field(default_factory=str)
    funds: Float = Field(default_factory=Float)
    specified_funds: Float = Field(default_factory=Float)
    executed_value: Float = Field(default_factory=Float)
    type: str = Field(default_factory=str)
    post_only: bool = Field(default_factory=bool)
    done_at: datetime = Field(default_factory=str)
    done_reason: str = Field(default_factory=str)
    filled_fees: Float = Field(default_factory=Float)
    filled_size: Float = Field(default_factory=Float)
    status: str = Field(default_factory=str)
    settled: bool = Field(default_factory=bool)
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type_convert(_from=float, _to=Float, by_alias=False)

    def to_serialize(self):
        """Serializable form of object."""
        return {
            k: str(v) if isinstance(v, datetime) else v
            for k, v in self.dict(by_alias=True).items()
        }

    @property
    def price(self) -> Float:
        """Price paid per unit of currency."""
        return self.executed_value / self.filled_size
        # if self.side == 'sell':
        #     return self.executed_value / self.filled_size
        # else:
        #     return self.executed_value / self.filled_size
    
    def text(
        self, sms: SMS, latest: Order, prior: Order, amt: Float, usd: Float,
        is_backtest: bool = False
    ) -> Order:
        """Text order details."""
        p1, p2 = prior.price, latest.price
        delta = Float((p2 / p1) - 1)
        txt = f"""
Trade Confirmation

Order Details
-------------
- Side: {self.side.title()}
- Asset: {self.product_id}
- Status: {'Settled' if self.settled else self.status.title()}
- Price: {latest.price.to_str()}
- vs. Prior: {delta.to_str(perc=True, rnd=3)}
- Executed: {self.executed_value.to_str()}
- Amount: {self.filled_size.to_str(perc=True)}

Account
--------
- {self.product_id}: {amt.arg()}
- USD:  {usd.to_str()}

Market price is {Float(latest.price).to_str()} at time of send.
"""
        if not is_backtest:
            sms.send(msg=txt)
        return self
