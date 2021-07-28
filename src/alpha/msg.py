"""
Unpacked ticker response.
"""
from __future__ import annotations

import time
import json

from pathlib import Path
from typing import Optional, Tuple, Dict

from pydantic import Field

from .base import Alpha
from .mocks.number import Float
from .static import iso_to_epoch, TICKER_DIR


class Msg(Alpha):
    """
    Set attributes on the Msg object based on ticker response.
    """

    # -- From Ticker --
    type: str = Field(default_factory=str)
    sequence: int = Field(default_factory=int)
    product_id: str = Field(default_factory=str)
    price: Float = Field(default_factory=Float)
    open_24h: Float = Field(default_factory=Float)
    volume_24h: Float = Field(default_factory=Float)
    high_24h: Float = Field(default_factory=Float)
    low_24h: Float = Field(default_factory=Float)
    volume_30d: Float = Field(default_factory=Float)
    best_bid: Float = Field(default_factory=Float)
    best_ask: Float = Field(default_factory=Float)
    side: str = Field(default_factory=str)
    time: str = Field(default_factory=str)
    trade_id: int = Field(default_factory=int)
    last_size: Float = Field(default_factory=Float)
    
    def __init__(self, **data):
        
        super().__init__(**data)
        
        self.type_convert(_from=float, _to=Float, by_alias=False)

    def to_local(self, _dir: Optional[Path] = None) -> Msg:
        """Serializes to local file."""
        _dir = _dir or (TICKER_DIR / 'messages')
        path = _dir / f"{self.product_id}~{self.sequence}.json"
        with open(path, 'w') as f:
            f.write(json.dumps(self.dict(by_alias=True), indent=4))
        return self

    def feed(self) -> Tuple[int, Dict[str, Float]]:
        """For DataFrame."""
        return int(iso_to_epoch(self.time) / 60), {'price': self.price}

    def __getitem__(self, item):
        """Getter for class."""
        return vars(self)[item]
