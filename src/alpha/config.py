"""
Configuration for Pydantic-based objects.
"""
from __future__ import annotations

import datetime
from collections.abc import Mapping
from pathlib import Path, WindowsPath
from typing import (
    Any, Callable, Dict, Set, Iterable
)

from pydantic import Extra


class Config:
    """
    Pydantic configuration specs.
    """

    extra = Extra.allow
    allow_population_by_field_name = True
    arbitrary_types_allowed = True
    json_encoders = {
        Path: lambda v: str(v.as_posix()),
        WindowsPath: lambda v: str(v.as_posix()),
        type: lambda v: str(v),
        Set: lambda v: list(v),
        datetime.datetime: lambda v: str(v),
    }

    def apply_map_by_type(self, attrs: Dict, typ: Any, func: Callable):
        """Recursively apply function to all values in a dictionary of type 'typ'.

        Args:
            attrs (dict):
                Dictionary to traverse.
            typ (Type):
                Type of object to apply function to.
            func (Callable):
                Function to apply to values of type `typ`.

        Returns:
            Altered dictionary with function applied to all keys and values
            matching `typ`.

        """
        if isinstance(attrs, Mapping):
            return {
                self.apply_map_by_type(k, typ, func):
                    self.apply_map_by_type(v, typ, func)
                for k, v in attrs.items()
            }
        elif isinstance(attrs, Iterable):
            return [self.apply_map_by_type(o, typ=typ, func=func) for o in attrs]
        elif isinstance(attrs, typ):
            return func(attrs)
        else:
            return attrs

    def serialize(self, as_dict: Dict) -> Dict:
        """Recursively applies `json_encoder` functions to all values of a dictionary."""
        serializable = as_dict
        for typ, serialize_func in self.json_encoders.items():
            serializable = self.apply_map_by_type(
                func=serialize_func,
                attrs=serializable,
                typ=typ,
            )
        return {
            k: str(v) if isinstance(v, datetime.datetime) else v
            for k, v in serializable.items()
        }
