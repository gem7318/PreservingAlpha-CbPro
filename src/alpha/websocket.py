"""
Coinbase Websocket (ticker message streaming).
"""
from __future__ import annotations

import os
import time

from contextlib import contextmanager
from typing import Optional, ContextManager, Dict

from cbpro import WebsocketClient

from .base import Alpha
from .ticker import Ticker
from .static import IS_RUNNING


class CoinBaseTicker(Alpha, WebsocketClient):
    """
    Stream ticker prices via websocket.
    """

    def __init__(
        self,
        file_nm: Optional[str] = None,
        load_messages: bool = True,
        collect: bool = False,
        **kwargs,
    ):

        Alpha.__init__(self=self, file_nm=file_nm, **kwargs)
        WebsocketClient.__init__(self=self, **self.args.websocket)

        #: int: Count of messages received
        self.cnt = int()
        
        #: bool: Insert messages into Mongo collections
        self.load_messages: bool = load_messages
        
        #: bool: Websocket is currently running
        self.running: bool = False
        
        #: float: Unix timestamp that the websocket was started
        self._started_at: float = float()
        
        #: Dict: Last message received
        self.msg: Dict = dict()
        
        #: Dict[str, Ticker]: Dictionary of Tickers by asset name
        self.existing: Dict[str, Ticker] = dict()
        
        #: bool: Store messages in a dictionary as they are received
        self.collect: bool = collect
        
        #: Dict[str, Dict[int, Dict]]: Dictionary of messages by asset, by index
        self.messages: Dict[str, Dict[int, Dict]] = {}

    def on_open(self):
        """Run file."""
        with open(IS_RUNNING, 'w') as f:
            f.write('<running>')

    def on_close(self):
        try:
            os.remove(str(IS_RUNNING))
        except IOError as e:
            raise e
        finally:
            self.running, self._started_at, self.cnt = False, float(), int()

    def on_message(self, msg) -> None:
        """Process a new ticker message."""
        if 'side' not in msg:
            return
        
        with self.new(msg=msg) as asset:
            
            ticker = self.existing.get(
                asset, Ticker(product_id=asset, is_test=self.is_test)
            )
            ticker.msg(msg=msg)
            
            with self.mongo_cache(asset, Ticker):
                self.existing[asset] = self._last = ticker
            
            if ticker and self.load_messages:
                ticker.insert()
                
            if self.collect:
                messages = self.messages.get(asset, dict())
                messages[len(messages) + 1] = msg
                self.messages[asset] = messages

    @contextmanager
    def new(self, msg: dict) -> ContextManager[str]:
        """Context of new message."""
        try:
            self.msg = msg
            self.cnt += 1
            yield msg['product_id']
        finally:
            return self

    def reset(self) -> CoinBaseTicker:
        """Resets count."""
        self.cnt = 0
        return self

    @contextmanager
    def stream(self) -> ContextManager[CoinBaseTicker]:
        """Stream ticker prices within context of a Mongo connection."""
        
        with self.db() as app:
        
            try:
                app._started, app.cnt = time.time(), int()
                print("<starting> Coinbase Ticker")
                app.start()
                while not app.cnt:
                    time.sleep(1)
                app.running = True
                print("..running: Coinbase Ticker")
                
                yield app
    
            except Exception as e:
                raise e
    
            finally:
                app.close()
                
    @contextmanager
    def db(
        self, db: Optional[str] = None, alias: Optional[str] = None
    ) -> ContextManager[CoinBaseTicker]:
        """Modifying connection context manager from Alpha."""
        with super().db(db=db, alias=alias) as connected:
            yield connected
            
    @property
    def time_running(self) -> int:
        """Time running for a given call to .stream()"""
        return int(time.time() - self._started_at) if self.running else 0
    
    def __int__(self):
        """int"""
        return self.cnt
    
    def __bool__(self):
        return not self.running
        
    def __str__(self):
        """str"""
        return f"CoinBaseTicker({self.cnt})"
