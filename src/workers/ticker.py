
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent.parent))
sys.path.insert(0, str(Path.cwd()))

from src.alpha.sms import SMS
from src.alpha.websocket import CoinBaseTicker
from src.alpha.errors import TickerConnectionClosed


def __run__():

	ticker = CoinBaseTicker()
	sms = SMS(**ticker.cfg['twilio'])
	
	try:
		sms.send(msg="started: Coinbase Ticker")
		with ticker.stream() as s:
			while s.running:
				pass
			
			raise TickerConnectionClosed(msg="Connection Lost")
	
	except TickerConnectionClosed as e:
		sms.send("<connection lost> Coinbase Ticker")
		
		time.sleep(2)
		__run__()


__run__()
