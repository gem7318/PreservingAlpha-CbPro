# preserving-alpha

[comment]: <> (TODO) Structural docs so you can remember how tf this all works

Protect portfolio downside and collect granular pricing data; project uses:
- Coinbase Pro websocket for ticker streaming
- MongoDB for data collection and storage
- pydantic for serialization
- Twilio for trade and extreme price action notifications

Light detail on execution mechanics in [src/workers/README.md](src/workers).

@author: Grant Murray

@originally-authored: 2020-11-02
