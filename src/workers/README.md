## ./src/workers

---

**::Context**

Project's workers, each performs operations based on the portfolio, assets, and frequency specifications in *alpha.toml*; they are designed to be run congruently.

---

**::Description**

The first two, *ticker* and *book*, collect data from the Coinbase Pro Websocket and API respectively; both of these run 24/7/365 and insert data directly into Mongo collections as it comes in. The last of the three, *portfolio*, watches these collections and operates on the data is at arrives in order to execute the strategy configured in *alpha.toml* against a single portfolio.

Slightly more granular information on each is included below.

---

- `ticker.py` opens a connection to the Coinbase Pro Websocket and collects
  the *ticker feed* for a configured set of assets; by default, *it will not insert more than one complete message (bid + offer) per-second, per-asset*

-   `book.py` collects order book data from the API based on simple throttling conditions; *the following options are configurable
    in alpha.toml*:
    -   Products (assets) to collect
    -   Order book granularity (levels 1-3)
    -   Frequency of collection for each level
-   `portfolio.py` executes a configured strategy against a single Coinbase Pro Portfolio;
    as of now, running strategies against different portfolios congruently is done by adding an additional worker following the structure of `portfolio.py`

