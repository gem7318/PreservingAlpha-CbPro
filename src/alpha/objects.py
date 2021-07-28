"""
Simple namespaces for common objects.
"""
from __future__ import annotations

from typing import List, Dict, Callable, Tuple, Union, Any, Optional

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """
    A single product / asset.
    """
    
    name: str = Field(alias='asset-id', default_factory=str)
    usd: str = Field(default_factory=str)
    
    def __init__(
        self,
        name: str,
        **data,
    ):
        super().__init__(**data)
        
        self.name = (name or self.name).lower()
        if '-' in self.name:
            self.name = self.name.split('-')[0]
        if self.name:
            self.usd = f"{self.name}-usd"
        
    def __str__(self):
        return self.usd


from pymongo import MongoClient
from pymongo.database import Collection, Database
from pymongo.results import InsertOneResult


class Args(BaseModel):
    """
    Container for Websocket, Mongo, and Twilio API arguments.
    """
    websocket: Dict
    mongo: Dict
    twilio: Dict

# -----------------------------------------------------------------------------

# TODO: Refactor these out of old codes


class Auth(BaseModel):
    """
    Authorization arguments.
    """
    key: str = Field(default_factory=str)
    secret: str = Field(default_factory=str)
    passphrase: str = Field(default_factory=str)


class Account(BaseModel):
    """
    A single portfolio.
    """
    # Account Name
    nm: str = Field(default_factory=str)

    # Asset Information
    asset_id: str = Field(default_factory=str)
    asset_id_usd: str = Field(default_factory=str)

    # Authorization Arguments
    auth: Auth = Field(default_factory=Auth)
