"""
Simple namespaces for common objects.
"""
from __future__ import annotations

import re

from contextlib import contextmanager
from typing import List, Dict, Union, Any, Optional, ContextManager

from pydantic import BaseModel, Field

from pymongo import MongoClient
from pymongo.database import (
    Collection as MongoCollection,
    Database as MongoDatabase,
)
from mongoengine import (
    connect,
    disconnect,
)

from src.alpha.config import Config


class Database(BaseModel):
    """
    Mongo Database.
    """
    
    #: MongoClient: MongoClient object
    client: MongoClient = Field(default=None, alias='client')
    
    #: str: Database name; defaults to 'coinbase'
    name: Optional[str] = Field(alias='name')
    
    def __init__(self, **data,):
        
        super().__init__(**data)
        
        self.name = self.name or 'coinbase'
    
    def collections(self) -> List[str]:
        """Collections as a string."""
        return self().list_collection_names()

    def drop(
        self, name: Optional[str] = None, pattern: Optional[str] = None
    ) -> None:
        """Drop collections."""
        if name:
            print(self().drop_collection(name))
        if pattern:
            for collection in self.collections():
                if re.findall(pattern, collection):
                    print(self().drop_collection(collection))
    
    def drop_tests(self, startswith: Optional[str] = None) -> None:
        """Drops all collections in a database that start with 'test_'."""
        startswith = startswith or 'test_'
        for collection in self.collections():
            if collection.startswith(startswith):
                print(self().drop_collection(collection))
    
    def __call__(self, *args, **kwargs) -> MongoDatabase:
        return self.client[self.name]
    
    class Config(Config):
        pass

 
class Collection(BaseModel):
    """
    Mongo Collection.
    """
    
    db: Database = Field(default=None, alias='db')
    name: Optional[str] = Field(default=None, alias='name')
    does_exist: Optional[bool] = Field(default=None)
    is_test: bool = Field(default=None, alias='is_test')
    
    def __init__(self, **data,):
        
        super().__init__(**data)

    def __str__(self) -> str:
        if not self.is_test and self.name:
            return self.name
        elif not self.is_test:
            return str()
        else:
            return f"test_{self.name}"

    def count(self, **kwargs) -> int:
        """Document count."""
        return self().estimated_document_count(**kwargs)

    def __call__(
        self, document: Optional[Dict] = None, *args, **kwargs
    ) -> MongoCollection:
        if document:
            # TODO: Add export here instead of on alpha
            return self().insert_one(document=document, **kwargs)
        return self.db()[str(self)]
        
    @property
    def exists(self) -> bool:
        """Collection exists."""
        if self.does_exist:
            return self.does_exist
        self.does_exist = str(self) in self.db.collections()
        return self.does_exist
    
    class Config(Config):
        pass
    
    
class Mongo(BaseModel):
    """
    Parent Mongo container.
    """
    
    defaults: Dict = Field(default_factory=dict, alias='defaults')
    client: MongoClient = Field(default_factory=MongoClient, alias='client')
    db: Database = Field(default=None, alias='db')
    collection: Collection = Field(default=None, alias='collection')
    is_test: bool = Field(default=None, alias='is_test')
    
    def __init__(
        self,
        defaults: Optional[Dict] = None,
        client: Optional[MongoClient] = None,
        **data,
    ):
        super().__init__(**data)
        
        self.defaults = defaults or dict()
        
        self.client: MongoClient = client
        
        self.db: Database = Database(client=self.client, name=self.db)
        
        self.collection: Collection = Collection(
            db=self.db,
            name=self.collection,
            is_test=self.is_test,
        )
        
    def databases(self, session: Any = None) -> List[str]:
        """List of databases."""
        return self.client.list_database_names(session=session)
        
    def updt(self, dtl: Dict[str, Union[MongoClient, Database, Collection]]):
        """Accepts cached connection details."""
        for attr_to_set, value_to_take in dtl.items():
            if attr_to_set in vars(self):
                vars(self)[attr_to_set] = value_to_take
    
    def dtl(self, client: Optional[MongoClient] = None):
        """Nests into MongoClient to get object-specific Collection."""
        self.client = self.db.client = client  # is what it is
        self.collection.db = self.db
        return {
            'client': self.client,
            'db': self.db,
            'collection': self.collection
        }
    
    @property
    def is_live(self) -> bool:
        """Connection is live."""
        return self.client is not None
    
    @contextmanager
    def connection(
        self, db: Optional[str] = None, alias: Optional[str] = None
    ) -> ContextManager[Mongo]:
        """Perform Mongo operations within the context of this connection.
        Args:
            db (Optional[str]):
                Name of database to connect to.
            alias (Optional[str]):
                Alias for database connection.
        """
        try:
            _ = self.connect(db=db, alias=alias)
            yield self
        except Exception as e:
            # TODO: Figure out what normally gets thrown / handle
            raise e
        finally:
            self.disconnect(alias=alias)
    
    def connect(
        self, db: Optional[str] = None, alias: Optional[str] = None
    ) -> MongoClient:
        """Establishes connection Mongo based on arguments or alpha.toml defaults.

        Args:
            db (Optional[str]):
                Name of database to connect to.
            alias (Optional[str]):
                Alias for database connection.
                
        Returns (MongoClient):
            Authenticated pymongo.MongoClient object.
            
        """
        if self.is_live:
            return self.client
        args = self.defaults
        if db:
            args['db'] = db
        if alias:
            args['alias'] = alias
        self.client = connect(**args)
        self.db.client = self.client
        self.collection.db = self.db
        return self.client

    # noinspection PyTypeChecker
    def disconnect(self, alias: Optional[str] = None) -> None:
        """Disconnect from Mongo Database.
        
        Args:
            alias (Optional[str]):
                Alias for database connection to disconnect from.
            
        """
        disconnect(alias=alias or self.defaults['alias'])
        self.client, self.db.client, self.collection.db = None, None, None


    def __bool__(self) -> bool:
        return self.client is not None

    def __call__(self, *args, **kwargs) -> MongoClient:
        return self.client
    
    class Config(Config):
        pass
