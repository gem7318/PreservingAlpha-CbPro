"""
File Stores:
    * Temporary static variables
    * Static functions used by multiple classes
"""
import os
import hashlib
from pathlib import Path
from types import MethodType
from typing import Any, Callable, Dict, List, Optional, Union

import json

import datetime
import dateutil.parser as dp

# -- Static Variables ---------------------------------------------------------

# -- Possible Order Statuses --
STATUSES = ['open', 'pending', 'active', 'done']

# -- Paths Relative to `static.alpha` --
HERE = Path(__file__).absolute()
ROOT = HERE.parent.parent.parent
SRC_DIR = ROOT / 'src'
DB_DIR = ROOT / 'hist'
TMP_DIR = ROOT / 'tmp'
STAGE_DIR = TMP_DIR / 'stage'
MODEL_DIR = ROOT / 'data' / 'models'
CRASH_DIR = TMP_DIR / 'crashes'
TICKER_DIR = TMP_DIR / 'ticker'
BOOK_DIR = TMP_DIR / 'book'
IS_RUNNING = TICKER_DIR / 'running.txt'


# -- Static Price Information --
PRICES_JSON = {p.stem: p for p in TICKER_DIR.iterdir() if p.suffix == '.json'}

# -- Days by Month Lookup (ETL) --
MONTH_DAY_LOOKUP = {
    1: 31,
    2: 28,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}

# -- Static Functions ---------------------------------------------------------


def asset_trunc(asset: str, lower: bool = False) -> str:
    """Returns the truncated name for an asset given an asset or and asset-pairs name.
    
    i.e. 'BTC' == asset_trunc('BTC-USD') == asset_trunc('BTC')
    
    """
    if len([p for p in asset.partition('-') if p]) == 3:
        asset = asset.partition('-')[0]
    return asset if lower else asset.lower()


def read_json(path: Path) -> Dict:
    """Reads in a json from file system."""
    with open(path, 'r') as r:
        return json.loads(r.read())


def messages(asset: str, to_insert: bool = False) -> Dict[int, Path]:
    """Ticker messages for asset by modified timestamp."""
    _dir = TICKER_DIR / 'messages'
    messages = {
        f.stat().st_mtime_ns: f
        for f in _dir.iterdir()
        if f.is_file()
        and str(asset).lower() in f.stem.lower()
    }
    return {
        i: messages[i]
        for i in (
            sorted(messages, reverse=True)[1:]
            if to_insert
            else sorted(messages, reverse=True)
        )
    }


def ticker_latest(asset: str, remove: bool = False) -> Dict:
    """Get the latest ticker message for an asset as a json."""
    # TODO: ticker_latest -> msg()
    _messages = messages(asset)
    try:
        path: Path = _messages[max(_messages)]
        with open(path, 'r') as r:
            raw = json.loads(r.read())
        if remove:
            os.remove(str(path))
        return raw
    except KeyError as e:
        raise e
    
    
def models(last: bool = True) -> Union[int, Dict[int, Path]]:
    """All models that have been serialized."""
    total = {int(p.stem.split('~')[0]): p for p in MODEL_DIR.iterdir()}
    if not last:
        return total
    return max(total)


def locate(file_nm: str, alt_path: Optional[Path] = None) -> Path:
    """Traverses file system from bottom up looking for a `file_nm`.
    
    Optionally falls back to `alt_path` if cannot be found.
    
    """
    found = None
    try:
        rents = [p for p in HERE.parents]
        rents.insert(0, HERE.parent)
        for rent in rents:
            if list(rent.rglob(file_nm)):
                found = list(rent.rglob(file_nm))[0]
                break
        if not found and alt_path:
            return alt_path
        if found.is_file():
            return found
    except FileNotFoundError as e:
        raise FileNotFoundError(e)


def iso_to_epoch(tm: Union[str, datetime.datetime]) -> float:
    """Converts iso to unix timestamp."""
    if not isinstance(tm, str):
        tm = str(tm)
    return dp.parse(tm).timestamp()


def batch_set_attrs(obj: Any, attrs: dict, to_none: bool = False):
    """Batch sets attributes on an object from a dictionary.

    Args:
        obj (Any):
            Object to set attributes on.
        attrs (dict):
            Dictionary containing attributes.
        to_none (bool):
            Set all of the object's attributes batching a key in `attrs`
            to `None`; defaults ot `False`.

    Returns (Any):
        Object post-setting attributes.

    """
    for k in set(vars(obj)).intersection(attrs):
        setattr(obj, k, None if to_none else attrs[k])
    return obj


def attrs_from_obj(
    obj: Any, within: Optional[List[str]] = None
) -> Dict[str, MethodType]:
    """Returns attributes/properties from an object as a dictionary."""
    return {
        str(m): getattr(obj, m)
        for m in dir(obj)
        if (m in within if within else True)
        and not isinstance(getattr(obj, m), Callable)
    }


def methods(
    obj: Any, within: Optional[List[str]] = None
) -> Dict[str, MethodType]:
    """Returns callable components of an object as a dictionary."""
    return {
        str(m): getattr(obj, m)
        for m in dir(obj)
        if (m in within if within else True)
        and isinstance(getattr(obj, m), MethodType)
    }


def md5_hash(hashable: str) -> str:
    """MD5 hash of a string."""
    hashed_base = hashlib.md5(hashable.encode("utf-8"))
    return hashed_base.hexdigest()
