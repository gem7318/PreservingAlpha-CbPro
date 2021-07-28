"""
A shamefully deep base class taken by majority of the object model.

.. combines:
    *   Parsing / Storage of alpha.toml
    *   Auth
        - Coinbase
        - Twilio
        - Mongo
    *   Serialization / De-Serialization (alpha.config.Config)
    *   Mongo Db Structure / Document Model
    
"""
from __future__ import annotations

import json
import datetime
import dateutil.parser as dp

from pathlib import Path
from contextlib import contextmanager
from typing import (
    Any, Dict, Union, Optional, ContextManager, Type
)

# 3rd party
import toml

from coinbasepro import AuthenticatedClient

from pymongo import MongoClient
from pymongo.results import InsertOneResult

from pydantic import BaseModel, Field
from pydantic.json import pydantic_encoder

# internal
from .sms import SMS
from .config import Config
from .mocks.number import Float
from .objects import (
    Args, Asset
)
from .. import (
    ROOT, TMP_DIR, ALPHA_CFG_FILE_NM
)
from src.alpha.mongo import Mongo



class Alpha(BaseModel, Config):
    """
    Base class; combines `alpha.toml` and keyword arguments.
    """
    
    created: datetime.datetime = Field(default_factory=datetime.datetime.now)
    
    def __init__(
        self,
        portfolio: Optional[str] = None,
        asset: Optional[str] = None,
        file_nm: Optional[str] = None,
        cb: Optional[AuthenticatedClient] = None,
        is_test: bool = False,
        _id_field: Optional[str] = None,
        **data,
    ):
        super().__init__(**data)
        
        #: str: Primary configuration file name; defaults to 'alpha.toml'
        self.file_nm = file_nm or ALPHA_CFG_FILE_NM
        
        #: pathlib.Path: Path to `alpha.toml`; assumes stored at project root
        self.path = ROOT / self.file_nm
        
        #: Dict: alpha.toml
        with open(self.path, 'r') as r:
            self.cfg = toml.load(r)
            
        #: Args: API arguments for Websocket feed, Mongo Auth, and Twilio Auth
        self.args = Args(
            websocket=self.cfg['websocket'],
            mongo=self.cfg['mongo'],
            twilio=self.cfg['twilio']
        )
        
        #: AuthenticatedClient: Authenticated CoinbasePro API
        self._cb: AuthenticatedClient = cb
        
        #: alpha.SMS: Authenticated Twilio API
        self.sms: SMS = SMS(**self.args.twilio)
        
        #: Dict[Dict[Type, Dict]]: Container for Mongo connections by type
        self.connections: Dict[Type, Dict[str, Dict]] = dict()
        
        #: Any: Last object instantiated; see self.mongo_child() for context
        self._last: Optional[Any] = None
        
        #: str: The name of the field on an object to use as the Document '_id'
        self.id_field = str()
        
        #: InsertOneResult: Response from collection.insert_one()
        self.response: InsertOneResult = (
            InsertOneResult(inserted_id=None, acknowledged=False)
        )
        
        #: str: Name of portfolio to trade with
        self._ptf: str = self.ptf_name(ptf=data.get('portfolio', portfolio))
        
        #: Optional[bool]: Indicates test or live collection
        self.is_test: Optional[bool] = data.get('is_test', is_test)
        
        #: Asset: Different string forms for an asset.
        self.asset_id: Asset = Asset(
            name=self.asset(data.get('asset', asset)),
            is_test=self.is_test,
        )
        
        self.mongo = Mongo(defaults=self.args.mongo, is_test=self.is_test)
        
        self.mongo.collection.name = str(self.asset_id).lower()
        
        #: Dict[str, bool]: Include / exclude attributes; see note directly below
        self.doc_fields = {
            
            #   This is a set of Alpha attributes to exclude when serializing;
            #   the below are defaults, intended to be modified and exist so
            #   that Alpha can be liberally extended, while serializing to a
            #   Database, Collection, and Document Schema defined by the
            #   derived class. This is very crude, but (for now) it's simple
            #   / testable / not causing problems.
            
            # :: configuration
            'file_nm': False,
            'path': False,
            'cfg': False,
            'args': False,
            
            # :: connections
            '_cb': False,
            'sms': False,
            'mongo': False,
            'connections': False,
            
            # :: other
            'response': False,
            '_last': False,
            'output_nm': False,
            'asset_id': False,
            '_ptf': False,
            'is_test': False,
            'doc_fields': False,
            'id_field': False,
        }
        
    def __post__init__(self, **data):
        """Post-processes / transforms attributes after being set on Alpha."""
        self.dict_update(  # Set attributes passed by field value
            **data
        ).type_convert(    # Force some conversions on extended types
            _from=float,
            _to=Float,
        )
    
    # -- Coinbase Pro API -----------------------------------------------------
    
    @property
    def cb(self) -> AuthenticatedClient:
        """Authenticated Coinbase Coinbase.
        
        Only authenticates if accessed; avoids connecting to the API every time
        an instance of a derived Alpha class is instantiated.
        
        """
        if self._cb:
            return self._cb
        self._cb = (
            AuthenticatedClient(**self._coinbase_auth(ptf=self._ptf))
        )
        return self._cb
    
    # -- Mongo / Database:: Connections ---------------------------------------
    
    @contextmanager
    def db(
        self, db: Optional[str] = None, alias: Optional[str] = None
    ) -> ContextManager[Alpha]:
        """Perform Mongo operations within the context of this connection.
        Args:
            db (Optional[str]):
                Name of database to connect to.
            alias (Optional[str]):
                Alias for database connection.
        """
        try:
            _ = self.mongo.connect(db=db, alias=alias)
            yield self
        except Exception as e:
            # TODO: Figure out what normally gets thrown here / handle
            raise e
        finally:
            self.mongo.disconnect(alias=alias)
            # self.connections = {}
        
    def cached(self, asset: str, typ: Type) -> Dict:
        """Checks for cached Mongo details."""
        cached_of_type = self.connections.get(typ)
        if cached_of_type:
            return cached_of_type.get(asset, dict())
        self.connections[typ] = {}
        return dict()
        
    @contextmanager
    def mongo_cache(self, asset: str, typ: Type) -> ContextManager[Dict]:
        """
        Checks for cached Mongo connections based on the class.
        """
        
        cached = self.cached(asset, typ)
        
        try:
            args = {}
            if isinstance(self.is_test, bool):
                args['is_test'] = self.is_test
            yield args
            
        except Exception:
            raise
        
        finally:
            if not cached and self.mongo:
                self.connections[typ][asset] = (
                    self._last.mongo.dtl(client=self.mongo.client)
                )
            elif cached:
                self._last.mongo.updt(cached)

    # -- Mongo / Database:: Operations ----------------------------------------
    
    def insert(
        self,
        connections: Optional[Dict[Type, Dict]] = None,
        export: bool = False,
        **kwargs,
    ) -> Alpha:
        """Insert Document fields from into Mongo collection."""
        _collection = self.mongo.collection
        if connections:
            cached = connections.get(
                type(self), dict()
            ).get(
                self.asset_id.name.lower(), dict()
            )
            if 'collection' in cached:
                _collection = cached['collection']
        self.response = _collection(document=self.to_mongo())
        if export:
            self.to_local(alt_file_nm=kwargs.get('alt_file_nm'))
        return self
    
    # -- Mongo / Database:: Collections ---------------------------------------
    
    @contextmanager
    def _op_validate_mongo(self, method: str) -> (
        ContextManager[Union[Type[Alpha], Alpha]]
    ):
        """Minimum validation prior to operating on a Collection."""
        try:
            if not self.mongo.collection.name and self.mongo.db.name:
                raise ValueError(
                    f".{method}() called prior to establishing a connection."
                )
            if not self.id_field:
                raise ValueError(
                    f".{method}() called prior to setting id_field."
                )
            yield
            
        except ValueError:
            raise
        
        finally:
            return self
    
    # -- Document Specific Serialization --------------------------------------
    
    def __json__(self, by_alias: bool = False, **kwargs) -> str:
        """json"""
        serializable = super().serialize(as_dict=self.dict(by_alias=by_alias))
        return json.dumps(
            obj=serializable,
            default=pydantic_encoder,
            **kwargs,
        )
    
    def json(self, by_alias: bool = False, **kwargs) -> str:
        """json API"""
        return self.__json__(by_alias=by_alias, **kwargs)
    
    def to_mongo(
        self, by_alias: bool = False, as_json: bool = False, **kwargs
    ) -> Union[Dict, str]:
        """Does serialization / namespace things to fit a Document's schema.
        
        *   Removes all fields from base model (Alpha) that are not explicitly
            denoted to be included in object's Collection
        *   Adds an explicit '_id' entry if set on the class
        *   Recursively applies the above to nested objects that also derive from
            Alpha; everything else is serialized by built-ins or Pydantic defaults.

        Args:
            by_alias (bool):
                Structure by field alias as opposed to field name.
            as_json (bool):
                Return object as a json string.
            **kwargs:
                Keyword arguments to pass to json.dumps() if `as_json=True`.

        Returns (Union[Dict, str]):
            A dictionary to pass to collection.insert() or similar method;
            json as as str if `as_json=True`

        """
        _apply_all_the_way_down = {
            **{'by_alias': by_alias, 'as_json': as_json},
            **kwargs,
        }
        document = {
            k: (
                v.to_mongo(**_apply_all_the_way_down)
                if issubclass(type(v), Alpha)
                else v
            )
            for k, v in vars(self).items()
            if self.doc_fields.get(k, True)
        }
        if self.id_field:
            document['_id'] = vars(self)[self.id_field]
        return (
            json.dumps(document, **kwargs)
            if as_json
            else document
        )

    def _export_path(self, file: str) -> Path:
        """Local serialization location."""
        return (
            (TMP_DIR / self.mongo.db.name)
            / (file or f"{self.mongo.collection.name}.json")
        )

    def to_local(self, alt_file_nm: Optional[str] = None) -> Alpha:
        """Serialize Document fields to a local target."""
        with open(self._export_path(alt_file_nm), 'w') as f:
            f.write(self.to_mongo(as_json=True, indent=4))
        return self
        
    def from_local(self, alt_file_nm: Optional[str] = None) -> Dict:
        """Serialize Document fields to a local target."""
        with open(self._export_path(alt_file_nm), 'r') as f:
            return json.load(f)
    
    def asset(self, asset: Optional[str] = None, is_test: bool = False) -> str:
        """Returns the collection name for an asset."""
        if not asset:
            asset = self.args.websocket['products'][0]  # default
        if '-' not in asset:
            asset = f"{asset}-usd"
        if is_test:
            asset = f"test_{asset}"
        return asset.lower()

    # -- Auth -----------------------------------------------------------------
    
    def ptf_name(self, ptf: Optional[str] = None) -> str:
        """Finds a portfolio name if not provided."""
        if ptf:
            return ptf
        portfolios = self.cfg['portfolios']
        default = portfolios.get('default')
        if not default:
            default = list(portfolios)[0]
        return default
    
    def _coinbase_auth(self, ptf: Optional[str] = None) -> Dict:
        """Returns the Coinbase Pro API arguments for a given portfolio, 'ptf'."""
        return self.cfg['portfolios'][self.ptf_name(ptf)]['auth']

    # -- Attribute Updates / Alternate Instantiation  -------------------------

    def dict_update(self, **kwargs) -> Alpha:
        """Updates current object's attributes with those from a dictionary."""
        # for k in set(kwargs).intersection(set(self)):
        for k in set(kwargs).intersection(set(vars(self))):
            vars(self)[k] = kwargs[k]
        return self
    
    def from_dict(self, args: Dict):
        """Accept a dictionary of arguments and updates the current object as if
        it were instantiated with those arguments."""
        return self.dict_update(obj=type(self)(**args))
    
    # -- Time Utilities -------------------------------------------------------
    
    @staticmethod
    def iso_to_epoch(iso: str) -> float:
        """Convert iso tmstmp as a string to unix timestamp as a float."""
        if not isinstance(iso, str):
            iso = str(iso)
        return dp.parse(iso).timestamp()
    
    @staticmethod
    def epoch_to_dt(epoch: float) -> datetime.datetime:
        """Convert unix timestamp as a float to datetime object."""
        return datetime.datetime.utcfromtimestamp(epoch)
    
    def iso_to_dt(self, iso: str) -> datetime.datetime:
        """Convert is tmstmp as a string to datetime object."""
        return self.epoch_to_dt(self.iso_to_epoch(iso))

    # -- Other ----------------------------------------------------------------

    def type_convert(self, _from, _to) -> None:
        """Converts attributes of self that are type '_from' to type '_to'.
         
         This is a shameful fix for not figuring out how to get Pydantic's
         factory functions to play nicely with classes that inherit from a
         built-in data type (e.g., 'Float').
         
         """
        for k, v in vars(self).items():
            if isinstance(v, _from):
                vars(self)[k] = _to(round(v, 3))
            elif issubclass(type(v), Alpha):
                v.type_convert(_from=_from, _to=_to)
    
    @property
    def configured_args(self) -> Dict:
        """Placeholder for configuration arguments of derived classes."""
        return dict()

    def __setattr__(self, key, value) -> Alpha:
        vars(self)[key] = value
        return self

    def __setitem__(self, key, value):
        vars(self)[key] = value
