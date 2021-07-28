"""
Parent package 'alpha'; stores directory paths relative to root of project.
"""

from pathlib import Path

# ----------------------
# -- Static Variables --
# ----------------------

# -- Primary Configuration File Name --
ALPHA_CFG_FILE_NM = 'alpha.toml'

# -- Possible Order Statuses --
STATUSES = ['open', 'pending', 'active', 'done']

# -- Directory Paths Relative to Project Root --
HERE = Path(__file__).absolute()
ROOT = HERE.parent.parent
SRC_DIR = ROOT / 'src'
DB_DIR = ROOT / 'hist'
TMP_DIR = ROOT / 'tmp'
CRASH_DIR = TMP_DIR / 'crashes'
TICKER_DIR = TMP_DIR / 'ticker'
BOOK_DIR = TMP_DIR / 'book'

# -- Static Price Information --
PRICES_JSON = {p.stem: p for p in TICKER_DIR.iterdir() if p.suffix == '.json'}

# -- Days by Month Lookup (ETL / Historic Prices Endpoint) --
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
