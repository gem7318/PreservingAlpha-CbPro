"""
Order Book object (client).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Optional, Union, Tuple, List

from pydantic import Field
from pymongo import MongoClient
from pymongo.database import Collection

from src.alpha.base import Alpha
from .mocks.number import Float

order_types = Union[
    # Structure of iterable returned from order book endpoint
    Tuple[float, float, int],  # Levels 1-2
    Tuple[float, float, str],  # Level 3
]
DATABASES = {
    # Maps order book level to the appropriate mongo db.
    1: 'book-best',
    2: 'book-50',
    3: 'book-full',
}


def find_collection(client: MongoClient, book: Dict) -> Collection:
    """Returns the order book collection for a given asset at a given level."""
    db = DATABASES[book['level']]
    return client[db][book['asset'].lower()]


class Order(Alpha):
    """
    Base class for an aggregate order on the books (levels 1-2).
    """
    
    #: Float: Asset price
    price: Float = Field(default_factory=Float)
    
    #: Float: Order size
    size: Float = Field(default_factory=Float)
    
    #: int: Number of orders for asset at price and size
    num_orders: int = Field(default_factory=int)
    
    def __init__(self, response: Optional[Tuple[str, str, str]] = None, **data):
        
        super().__init__(**data)
        
        if response:
            self.price, self.size, self.num_orders = (
                Float(response[0]), Float(response[1]), int(response[2])
            )
            
        self.type_convert(float, Float)
        
    def __str__(self) -> str:
        _asset = self.mongo.collection.name
        _price = self.price.to_str()
        _size = self.size.arg()
        return f"Order(asset='{_asset}', price='{_price}', size='{_size}')"
    
    def __repr__(self) -> str:
        return str(self)


class OrderL3(Alpha):
    """
    Base class for a granular / order-level order on the books (level 3).
    """
    
    #: Float: Asset price
    price: Float = Field(default_factory=Float)
    
    #: Float: Order size
    size: Float = Field(default_factory=Float)
    
    #: str: Order ID
    order_id: str = Field(default_factory=str)
    
    def __init__(self, response: Optional[Tuple[str, str, str]] = None, **data):
        
        super().__init__(**data)
        
        if response:
            self.price, self.size, self.order_id = (
                Float(response[0]), Float(response[1]), response[2]
            )


class OrderBook(Alpha):
    """
    A single order within a response from the order book endpoint.
    
    Structure of tuple for each level is as follows:
    *   level 1: (price, size, num_orders)
    *   level 2: (price, size, num_orders)
    *   level 3: (prize, size, order_id)
    
    """
    
    #: datetime: Creation timestamp
    time: datetime = Field(default_factory=datetime.now)
    
    #: int: Response sequence
    sequence: int = Field(default_factory=int)
    
    #: int: Order book granularity (1 - 3)
    level: int = Field(default_factory=int, alias='level')
    
    def __init__(
        self,
        asset: Optional[str] = None,
        level: Optional[int] = None,
        is_test: Optional[bool] = None,
        **data,
    ):
        super().__init__(
            asset=asset,
            is_test=is_test,
            db_nm=DATABASES[data.get('level', (level or 2))],
            **data,
        )
        
        self.mongo.db.name = DATABASES[data.get('level', (level or 2))]
        
        #: str: Collection ID / index
        self.field_id = self.time
    
        #: List[Union[Order, OrderL3]]: Sell side offers; levels 1-2 or 3
        self.asks: List[Union[Order, OrderL3]] = list()
        
        #: List[Union[Order, OrderL3]]: Buy side offers; levels 1-2 or 3
        self.bids: List[Union[Order, OrderL3]] = list()
        from typing import Set
        
        #: List[str]: Static list; ['bids', 'asks']
        self.sides: List[str] = ['bids', 'asks']
        
        # -- unpack order book based on level --
        if all(bool(data.get(side)) for side in self.sides):
            self.unpack(
                data=data,
                level=level,
                is_mongo=bool(data.get('_id'))
            )
        
    def unpack(
        self, data: Dict, level: Optional[int] = None, is_mongo: bool = False
    ) -> OrderBook:
        """Unpack order book response or Mongo document."""
        level = level or 2
        _OrderObj = (
            Order
            if level in {1, 2}
            else OrderL3
        )
        for side in self.sides:
            vars(self)[side] = [
                _OrderObj(
                    **({'response': response} if not is_mongo else response)
                )
                for response in data[side]
            ]
        return self
    
    def to_mongo(
        self, by_alias: bool = False, as_json: bool = False, **kwargs
    ) -> Union[Dict, str]:
        """Superseding Alpha's serialization method to jsonify bids/asks."""
        document = super().to_mongo(by_alias=by_alias, as_json=as_json, **kwargs)
        for side in self.sides:
            document[side] = [
                b.to_mongo(by_alias=by_alias, as_json=as_json, **kwargs)
                for b in vars(self)[side]
            ]
        self.sides = list(self.sides)
        return (
            json.dumps(document, **kwargs)
            if as_json
            else document
        )
    
    def __str__(self):
        return f"OrderBook(asset='{str(self.asset_id).upper()}', level={self.level})"

    def __repr__(self):
        # TODO
        return str(self)
