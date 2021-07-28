"""
CoinBasePro API Coinbase.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Optional, ContextManager, Dict, Union

from src.alpha.base import Alpha
from src.alpha.book import OrderBook


class Coinbase(Alpha):
    """
    A single portfolio.
    """
    
    @contextmanager
    def db(
        self, db: Optional[str] = None, alias: Optional[str] = None
    ) -> ContextManager[Coinbase]:
        """Superseding Alpha connection context for editor hints on Coinbase class."""
        with super().db(db=db, alias=alias):
            yield self
            
    @contextmanager
    def mongo_prep(self, response: Dict, **kwargs) -> ContextManager[Dict]:
        """Prep API response for Pydantic model / document schema."""
        # TODO: Base class
        prepped = response.copy()
        try:
            for k, v in kwargs.items():
                prepped[k] = kwargs[k]
            yield prepped
        except KeyError as e:
            raise e
        finally:
            pass

    def order_book(
        self, asset: Optional[str] = None, level: Optional[int] = None, raw: bool = False,
    ) -> Union[OrderBook, Dict]:
        """Get order book for an asset."""
        _asset, _level = asset or str(self.asset_id), level or 2
        
        response = self.cb.get_product_order_book(
            product_id=_asset.upper(),
            level=_level,
        )
        
        if raw:
            return response
        
        to_swap = {'asset': _asset, 'level': _level}
        with self.mongo_prep(response=response, **to_swap) as r_schema:
            pass
        with self.mongo_cache(asset, OrderBook) as args:
            r_schema.update(args)
            self._last = OrderBook(**r_schema)
        return self._last
