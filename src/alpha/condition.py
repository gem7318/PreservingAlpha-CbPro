"""
A single buy/sell condition, such as the following:

(a) toml: ['dema', '15', '30', '-0.003']
    desc: '15 vs 30 minute double exponential moving average is < (0.3%)'
(b) toml: ['max', '0', '-1', '1']
    desc: '100% of historic max'
(c) toml: ['spread~h', '0', '6', '0.98']
    desc: '98% of spread for the last 6 records'

"""
from __future__ import annotations

from typing import Optional, Dict, List, Union, Set

from pydantic import Field

from src.alpha.base import Alpha
from src.alpha.number import Float
from src.alpha.static import methods
from src.alpha.coinframe import CoinFrame


# noinspection PyTypeChecker
class Calc(Alpha):
    """
    A single calculation.
    """
    raw: List[str]
    nm: str = Field(default_factory=str)
    bound: float = Field(default_factory=float)
    val: Float = Field(default_factory=float)
    is_ma: bool = Field(default_factory=bool)

    def __init__(self, **data):  # sourcery skip: assign-if-exp
        
        super().__init__(**data)
        
        if len(self.raw) == 2:
            self.nm, self.bound = self.raw[0], Float(self.raw[1])
        else:
            self.nm, self.bound = self.raw[0], -1
        
        if self.nm.endswith('*'):
            self.nm, self.bound = self.nm[:-1], Float(self.bound) * 60
        elif self.nm.endswith('**'):
            self.nm, self.bound = self.nm[:-2], Float(self.bound) * 60
            
        self.is_ma = self.nm in dir(CoinFrame())
        
        self.type_convert(_from=float, _to=Float, by_alias=False)
        
    @property
    def name(self):
        """Name in master 'calcs' dictionary."""
        if isinstance(self.bound, Float):
            return f"{self.nm} (n={int(self.bound)})"
        return self.nm
        
    def d(self):
        """Display."""
        if isinstance(self.bound, Float):
            bound = self.bound
            b_str = str()
            if self.bound >= 60:
                b_str = f"{int(bound / 60)}h"
            b_str = b_str or f"{int(bound)}m"
            return f"{self.nm}-{b_str}: {self.val.to_str()}"
        return f"{self.nm}: {self.val.to_str()}"

    def bnd(self):
        """Display."""
        if isinstance(self.bound, Float):
            bound = self.bound
            b_str = str()
            if self.bound >= 60:
                b_str = f"{int(bound / 60)}h"
            b_str = b_str or f"{int(bound)}m"
            return f"{self.nm}-{b_str}"
        return self.nm
        
    def __float__(self):
        """Float representation."""
        return float(self.val)
    
    def __bool__(self):
        """Bool representation (value is populated)."""
        return bool(self.val)
        
    def __truediv__(self, other) -> Float:
        """Operation -> division."""
        if bool(self) and bool(other):
            return Float(float(self) / Float(other))
        return Float()


class Condition(Alpha):
    """
    Set attributes on the Msg object based on ticker response.
    """
    
    raw: List[List[str]]
    
    t_r: str = Field(default_factory=str)
    t: float = Field(default_factory=float)
    
    gt: bool = Field(default_factory=bool)
    
    calcs: Dict[int, Calc] = Field(default_factory=dict)
    
    mode: str
    
    # buying: bool = Field(default_factory=bool)

    def __init__(self, **data):
        
        super().__init__(**data)
        
        self.calcs = {
            1: Calc(raw=self.raw[0]),
            2: Calc(raw=self.raw[1]),
        }
        
        self.t_r = self.raw[-1][0]
        
        self.eq = bool(self.t_r.endswith('**'))
        self.gt = bool(self.t_r.endswith('*') and not self.t_r.endswith('**'))
        
        if self.gt:
            self.t = float(self.t_r[:-1])
        elif self.eq:
            self.t = float(self.t_r[:-2])
        else:
            self.t = float(self.t_r)
        # self.t = float(self.t_r[:-1]) if self.gt else float(self.t_r)
        
        self.type_convert(_from=float, _to=Float, by_alias=False)
    
    @property
    def actual(self) -> Float:
        """Calculation of bound."""
        if any(
            c.nm == 'price-last' and not bool(c)
            for c in self.calcs.values()
        ):
            return Float()
        return self.calcs[2] / self.calcs[1]
    
    def apply(self, calcs: Dict[str, float]) -> None:
        """Set calculated values on both Calc(s)."""
        from src.alpha.errors import ConditionNotFoundError
        for i, c in self.calcs.items():
            match = [v for k, v in calcs.items() if k == c.name]
            if not match:
                raise ConditionNotFoundError(
                    msg=f"'{c.name}' not found in {list(calcs)}"
                )
            c.val = Float(match[0])
            
    @property
    def _s(self) -> str:
        """Greater than/less than symbol."""
        if self.gt:
            return '>'
        if self.eq:
            return '='
        return '<'
        
    def c(self):
        """Condition as a string."""
        c1, c2 = self.calcs[1], self.calcs[2]
        return f"{c1.bnd()} vs. {c2.bnd()} {self._s} {self.t}"
    
    def n(self):
        """Name."""
        return f"Condition({self.c()})"
    
    def d(self):
        """Display."""
        otc = bool(self)
        otc1 = f"({self.mode})" if otc else '(hold)'
        c1, c2 = self.calcs[1], self.calcs[2]
        v1, v2 = c1.val.to_str(), c2.val.to_str()
        act = round(self.actual, 3)
        args = [
            f"{otc1.rjust(6)} {c2.bnd()} vs. {c1.bnd()}",
            f"\t- {v2} vs. {v1}",
            f"\t- Current {act}; Targeting {self._s}{self.t}",
        ]
        return '\n'.join(args)

    @property
    def contents(self) -> Set[str]:
        """Names of calcs."""
        return {c.name for c in self.calcs.values()}
    
    def __bool__(self):
        """Boolean representation of Condition."""
        if any(
            c.nm == 'price-last' and not bool(c)
            for c in self.calcs.values()
        ):
            return True
        if self.gt:
            return self.actual > self.t
        if self.eq:
            return self.actual == self.t
        return self.actual < self.t
