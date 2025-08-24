# compute_spx.py

from analysis_core import compute_stats
from datetime import datetime

if __name__ == '__main__':
    compute_stats(
        input_source='ticker.xlsx',
        periods={'1m': 1, '3m': 3, '6m': 6, '1y': 12},
        output_file=f"output_spx_{datetime.today():%Y-%m-%d}.xlsx",
        trading_days=252,
        ticker_col='SPX Ticker',
        name_col='SPX Name'
    )