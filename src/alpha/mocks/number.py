"""
Extending Float object for easier conversion between historical types; used
for maths and string representations required by the API.
"""
from __future__ import annotations

import locale
from typing import Union, Optional

locale.setlocale(locale.LC_ALL, '')
locale.format_string('%d', 1000, grouping=True)


class Float(float):
    """
    Extended float class.
    """
    
    def __init__(self, val: Optional[float, str] = None):
        
        if str(val).endswith('*'):
            val = float(val[:-1])*60
            
        if val:
            val = round(float(val), 3)
            
        float.__init__(val or float())
        
        self.act: float = float()
        
    def vs_act(self, act: Optional[Union[Float, float]] = None) -> Float:
        """Subtracts self from `act`."""
        act = act or self.act
        return Float(act - self)
     
    def to_str(self, perc: bool = False, rnd: Optional[int] = None) -> str:
        """String representation."""
        val = self if self >= 0 else self * -1
        if perc:
            val = round(val, rnd or 2)
            as_str = f"{val}%"
            return f"{as_str}" if self >= 0 else f"({as_str})"
        val = int(val)
        as_str = f"${locale.format_string('%d', val, grouping=True)}"
        return f"{as_str}" if self >= 0 else f"({as_str})"
    
    def arg(self):
        """Representation as expected by the API's `funds` and `size` parameters."""
        return str(round(self, 2))

    def __add__(self, other) -> Float:
        """Operation -> addition."""
        return Float(float(self) + float(other))
    
    def __sub__(self, other) -> Float:
        """Operation -> subtraction."""
        return Float(float(self) - float(other))
    
    def __mul__(self, other) -> Float:
        """Operation -> multiplication."""
        return Float(float(self) * float(other))
    
    def __truediv__(self, other) -> Float:
        """Operation -> division."""
        return Float(float(self) / float(other))

    def __setattr__(self, key, value):
        vars(self)[key] = value

    def __setitem__(self, key, value):
        vars(self)[key] = value
