from analysis_core import compute_stats
from datetime import datetime

if __name__ == '__main__':
    source = ['AXP', 'BAC', 'C','CSCO', 'JPM', 'KO', 'MCO', 'PLTR']
    periods = {'1m': 1, '2m': 2, '3m': 3, '6m': 6, '1y': 12}
    compute_stats(source, periods, output_file=f"output_from_list_{datetime.today():%Y-%m-%d}.xlsx")