
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent.parent))
sys.path.insert(0, str(Path.cwd()))

from src.alpha.client import Coinbase


# noinspection PyBroadException
def __run__():

    ptf = Coinbase()
    ptf.sms.send(msg="started: Coinbase Order Book")

    try:
        assets = ptf.args.websocket['products']
        with ptf.db() as client:
            i = 0
            sleep = 10
            while True:
                for i2, asset in enumerate(assets, start=1):
                    _mid = client.order_book(asset=asset, level=2).insert()
                    # print(f"{i}.{i2}: {_mid.asset()}")
                    i += 10
                    if i % 1800 == 0:
                        for a in assets:
                            _full = client.order_book(asset=a, level=3).insert()
                            time.sleep(3)
                    time.sleep(2)
                time.sleep(sleep)

    except Exception as e:  # note: not raising
        raise e


__run__()
