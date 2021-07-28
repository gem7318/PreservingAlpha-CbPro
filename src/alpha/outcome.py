"""
A full set of buy or sell conditions within a portfolio.
"""
from __future__ import annotations

from typing import Optional, Dict, List, Union, Set

from pydantic import Field

from src.alpha.base import Alpha
from src.alpha.number import Float
from src.alpha.condition import Condition, Calc


class Outcome:
    """
    Evaluates buy or sell conditions.
    """
    def __init__(
        self,
        nm: str,
        conditions: List[List[List[str]]],
        mode: str,
    ):
        self.nm = nm
        self._cds = conditions
        self.mode = mode
        self.cds: Dict[int, Condition] = {}
        for i, r in enumerate(self._cds, start=1):
            self.cds[i] = Condition(raw=r, mode=mode)
          
    @property
    def ub(self):
        """Max bound."""
        return max(
            c.bound
            for cd in self.cds.values()
            for c in cd.calcs.values()
            if c.bound
        )
    
    def calcs(self, ma: bool = False, other: bool = False) -> Dict[str, Calc]:
        """All calcs from conditions."""
        total: Dict[str, Calc] = {
            c.name: c
            for cd in self.cds.values()
            for c in cd.calcs.values()
        }
        if ma:
            return {nm: c for nm, c in total.items() if c.is_ma}
        if other:
            return {nm: c for nm, c in total.items() if not c.is_ma}
        return total
    
    def apply(self, calcs: Dict[str, float]) -> None:
        """Apply latest actual to each calc."""
        _ = [r.apply(calcs) for r in self.cds.values()]
        
    def dtl(self, r: bool = False) -> Union[None, str]:
        """Details as text."""
        dtl = [r.d() for r in self.cds.values()]
        dtl.insert(0, self.title(r=True))
        dtl = '\n'.join(dtl)
        if r:
            return dtl
        print(dtl)
        
    def title(self, r: bool = False) -> Union[None, str]:
        """Name as text."""
        nm = self.nm.title()
        title = f"{nm}\n{'-' * (len(nm) + 1)}"
        if r:
            return title
        print(title)
        
    def __bool__(self) -> bool:
        """Boolean representation (all Conditions evaluate to True)."""
        return all(self.cds.values())
    
    def __str__(self) -> str:
        cds = [c.c() for c in self.cds.values()]
        return f"Outcome({'; '.join(cds)})"
    
    def __repr__(self) -> str:
        return f"Outcome(nm='{self.nm}', mode='{self.mode}', conditions={len(self.cds)})"
