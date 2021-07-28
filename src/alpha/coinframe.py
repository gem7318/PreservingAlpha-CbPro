"""
DataFrame extensions; performs primary trailing operations on a DataFrame.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Union, Tuple

import pandas as pd

from src.alpha.errors import ExpiredPriceDataError, BackTestCompletedError
from src.alpha.mocks.number import Float
from src.alpha.msg import Msg
from src.alpha.static import ticker_latest


@pd.api.extensions.register_dataframe_accessor("cb")
class CoinFrame:
    """
    Extends a :class:`~pandas.DataFrame` with a ``.cb`` entry point.
    """

    def __init__(
            self,
            df: Optional[pd.DataFrame] = None,
            i: Optional[int] = None,
            n: Optional[int] = None,
            e: Optional[int] = None,
            **kwargs,
    ):
        super().__init__()
        self.asset_id: str = kwargs.get('asset')
        self.i = i or int()
        self.e = e or (int() + 1)
        self.calcs: Dict[str, Float] = dict()
        
        self._obj: pd.DataFrame = df
        self._src: Dict = dict()

        self.is_backtest: bool = kwargs.get('is_backtest', bool())
        self._src_backtest: Dict = dict()
        self.n: int = n or int()
        
    # Descriptive Properties / Methods ----------------------------------------
    
    # noinspection PyTypeChecker
    def first(self, backtest: bool = False) -> int:
        """Unix timestamp of first record."""
        return min(self.src(backtest=backtest))

    # noinspection PyTypeChecker
    def last(self, backtest: bool = False) -> int:
        """Unix timestamp of last record."""
        return max(self.src(backtest=backtest))

    @property
    def columns(self) -> List[str]:
        """CoinFrame's columns."""
        return list(self._obj.columns)
    
    @property
    def df(self) -> pd.DataFrame:
        """DataFrame accessor for the CoinFrame."""
        return self._obj
    
    def col(self, n: Optional[int] = None) -> pd.DataFrame:
        """Column 'n' from CoinFrame (0-based)"""
        n = n or 0
        return self._obj[self.columns[n]]

    # -- Operations / Calculations --------------------------------------------

    def ema(
            self,
            n: Optional[int] = None,
            suffix: bool = True,
            drop_cols: bool = True,
            on_copy: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Exponential moving average for trailing 'n' records."""
        df = self._obj
        n = int(n or self.i)
        if on_copy:
            df = self._obj.copy(deep=True)
            
        sfx = f"_{n}" if suffix else str()
        multiplier = 2 / (n + 1)
        
        _sfx = sfx.strip('_')
        sma_col = f'sma (n={_sfx})'
        ema1_col = f'ema (i=1, n={_sfx})'
        
        df_rolling_n = df.rolling(n).mean().rename(columns={'price': sma_col})
        df = pd.concat(objs=[df, df_rolling_n], axis=1)
        df[ema1_col] = (
            (df.price * multiplier)
            + (df[sma_col].shift(1) * (1 - multiplier))
        )
        
        if drop_cols:
            for col in [sma_col, 'price']:
                df.drop(columns=[col], inplace=True)
        
        return self.cache(df)

    def dema(
            self,
            n: Optional[int] = None,
            suffix: bool = True,
            drop_cols: bool = True,
            on_copy: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Double exponential moving average for trailing 'n' records."""
        df = self._obj
        n = int(n or self.i)
        if on_copy:
            df = self._obj.copy(deep=True)
            
        sfx = f"_{n}" if suffix else str()
        multiplier = 2 / (n + 1)
        
        _sfx = sfx.strip('_')
        
        sma_col = f'sma (n={_sfx})'
        
        ema1_col = f'ema (i=1, n={_sfx})'
        ema2_col = f'ema2 (i=2, n={_sfx})'
        
        dema_col = f'dema (n={_sfx})'
        
        df = pd.concat(
            [df, df.rolling(n).mean().rename(columns={'price': sma_col})],
            axis=1,
        )
        
        df[ema1_col] = (df.price * multiplier) + (df[sma_col].shift(1) * (1 - multiplier))
        df[ema2_col] = (df.price * multiplier) + (df[ema1_col].shift(1) * (1 - multiplier))
        
        df[dema_col] = (2 * df[ema1_col]) - df[ema2_col]
        
        if drop_cols:
            for col in [sma_col, ema1_col, ema2_col, 'price']:
                df.drop(columns=[col], inplace=True)
        
        return self.cache(df)
    
    def dema_delta(
            self,
            n1: int,
            n2: int,
            suffix: bool = True,
            drop_cols: bool = True,
            on_copy: Optional[bool] = None,
    ) -> pd.DataFrame:
        """Calculate difference in two exponential moving averages."""
        df_n1 = self.dema(n1, suffix, drop_cols, on_copy)
        df_n2 = self.dema(n2, suffix, drop_cols, on_copy)
        suffix = f"dema_{n1}_vs_{n2}"
        df = (df_n1[list(df_n1.columns)[0]] / df_n2[list(df_n2.columns)[0]]) - 1
        df.columns = suffix
        return df.dropna()
        
    def price(self, n: Optional[int] = None) -> pd.DataFrame:
        """Current price."""
        df = self._obj.tail(n or 1).copy(deep=True)
        df.columns = ['price']
        return self.cache(df)
    
    def max(self, n: Optional[int] = None) -> pd.DataFrame:
        """Trailing max price over 'n' time periods."""
        n = int(n) or int()
        suffix = f"max (n={n or 'hist'})"
        df = self._obj.rolling(n).max() if n else self._obj.cummax()
        return self.cache(df.rename(columns={self.columns[0]: suffix}))

    def min(self, n: Optional[int] = None) -> pd.DataFrame:
        """Trailing min price over 'n' time periods."""
        n = int(n) or int()
        suffix = f"min (n={n or 'hist'})"
        df = self._obj.rolling(n).min() if n > 0 else self._obj.cummin()
        return self.cache(df.rename(columns={self.columns[0]: suffix}))
    
    def spread(self, n: Optional[int] = None) -> pd.DataFrame:
        """Trailing spread over 'n' time periods."""
        suffix = f"spread (n={n if n or n > 1 else 'hist'})"
        df_max = self.max(n)
        df_min = self.min(n)
        df_spread = df_max.max_hist - df_min.min_hist
        df_spread.columns = [suffix]
        return self.cache(df_spread)
    
    # -- State Management -----------------------------------------------------
    
    def src(self, r: bool = False, backtest: bool = False, i: Optional[int] = None) -> Dict[int, Dict]:
        """Data contained as an index-oriented dictionary."""
        if not self._src or r:
            self._src = self._obj.to_dict(orient='index')
        src = self._src if not backtest else self._src_backtest
        return src if not i else src[i]
    
    def from_dict(self, src: Optional[Dict[int, Dict[str, Float]]] = None) -> CoinFrame:
        src = src or self._src
        self._obj = pd.DataFrame().from_dict(data=src, orient='index')
        self._obj.index.name = 'tm_unix_m'
        return self
    
    def update(self, asset: Optional[str] = None) -> CoinFrame:
        """Update contents from a feed/ticker response."""
        asset = asset or self.asset_id
        if not asset:
            raise ValueError(
                "CoinFrame.update() called without an asset_id provided or in its"
                "`asset_id` attribute."
            )
        if self.is_backtest:
            return self._update_backtest()
        tmstmp, price = Msg(**ticker_latest(asset=asset, remove=False)).feed()
        if (tmstmp - self.last()) > 0:
            _ = self._src.pop(self.last())
        self._src[tmstmp] = price
        return self.from_dict()
    
    def _update_backtest(self) -> CoinFrame:
        """Update contents from back-testing source data."""
        try:
            tmstmp = self.first(backtest=True)  # next mock ticker message
            _ = self._src.pop(self.first())     # oldest record in live data
            price = self._src_backtest.pop(     # next mock price
                self.first(backtest=True)
            )
            self._src[tmstmp] = price
            return self.from_dict()
        except ValueError as e:
            raise BackTestCompletedError(msg="Back-test finished.") from e
    
    def cache(self, df: pd.DataFrame) -> pd.DataFrame:
        """Saves last value to 'calcs' attribute."""
        for k, v in df.tail(1).to_dict(orient='records')[0].items():
            self.calcs[k] = v
        return df.dropna()
    
    def validate(self, is_feed: bool = False, r: bool = False) -> Union[None, CoinFrame]:
        """Validates DataFrame returned by db.price()."""
        latest = self._obj.tail(1).to_dict(orient='records')[0]
        if not is_feed and not self.is_backtest:
            e = latest['elapsed_m']
            if e > self.e:
                raise ExpiredPriceDataError(
                    msg=f"Price hist is {e} minutes old; threshold is {self.e}."
                )
        if self._obj.index.name != 'tm_unix_m':
            self._obj.set_index(
                keys=['tm_unix_m'],
                inplace=True,
            )
        self._obj.drop(
            columns=[c for c in self.columns if c.lower() != 'price'],
            inplace=True,
        )
        if r:
            return self

    # Back-Testing ------------------------------------------------------------
    
    def prep_backtest(self) -> None:
        """Reshape underlying data for back-testing."""
        self.validate()
        self._src_backtest = {
            tm: price
            for tm, price in self.src().items()
            if tm >= (self.first() + (self.n * 2))
        }
        for i in self._src_backtest:
            _ = self._src.pop(i)
        _ = self.from_dict()
        
    
    def __call__(self, *args, **kwargs) -> pd.DataFrame:
        return self._obj
    
    def __str__(self):
        return f"CoinFrame(depth={self._obj.shape[0]})"
