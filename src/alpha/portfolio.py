"""
Coinbase Pro Portfolio: Trading Class.
"""
from __future__ import annotations

from typing import Dict, Optional

from .base import Alpha
from .objects import Asset
from .mocks.number import Float


class Portfolio(Alpha):
    """
    A single portfolio.
    """
    
    def __init__(
            self,
            portfolio: Optional[str] = None,
            **data,
    ):
        
        super().__init__(portfolio=portfolio, **data)
        
        # -- A Portfolio's Configuration --
        portfolio = self.cfg['portfolios'][self._ptf]
        
        # #: Asset: Asset to trade
        self.asset_id: Asset = Asset(portfolio['asset'])
        
        #: Float: Percentage of account to trade with contained strategy
        self.allocation: Float = Float(portfolio.get('account-allocation', 1))
        
        #: Dict: API authentication for the portfolio
        self.auth: Dict = portfolio['auth']
        
        #: Dict: Buy strategies for portfolio
        self.buy: Dict = portfolio['buy']
        
        #: Sell: Sell strategies for portfolio
        self.sell: Dict = portfolio['sell']
        
        self.doc_fields['asset_id'] = True
        
        self.__post__init__(**data)
