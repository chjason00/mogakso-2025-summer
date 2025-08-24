# core.py

rf_1m = 0.04236
rf_2m = 0.04396
rf_3m = 0.04354
rf_6m = 0.04299
rf_1y = 0.04107

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io
from contextlib import redirect_stdout, redirect_stderr

def load_input(input_source, ticker_col='Ticker', name_col='Name'):
    if isinstance(input_source, list):
        return pd.DataFrame({
            'Ticker': [str(t) for t in input_source],
            'Name':   [str(t) for t in input_source],
        })
    elif isinstance(input_source, str):
        df = pd.read_excel(input_source)
    elif isinstance(input_source, pd.DataFrame):
        df = input_source.copy()
    else:
        raise ValueError("input_source must be a list, DataFrame, or file path.")

    if ticker_col not in df.columns or name_col not in df.columns:
        raise KeyError(f"Expected columns '{ticker_col}' and '{name_col}' not found in input.")

    df = df[[ticker_col, name_col]].dropna(subset=[ticker_col])
    df.columns = ['Ticker', 'Name']
    df['Ticker'] = df['Ticker'].astype(str)
    return df


def compute_sharpe_ratio(avg_return: float, volatility: float, risk_free_rate: float = 0.03):
    """
    # 새로 추가된 함수: 샤프 비율 계산
    avg_return: 연환산 수익률
    volatility: 연환산 변동성
    risk_free_rate: 무위험 수익률 (기본 3%)
    """
    if volatility == 0 or np.isnan(volatility):
        return np.nan
    return (avg_return - risk_free_rate) / volatility

def fetch_price_series(ticker, start_date, end_date=None):
    if "." in ticker and "KS" not in ticker:
        ticker = ticker.replace('.', '-')
    if ticker.upper() in ['SPX', 'SPX INDEX']:
        code = '^GSPC'
    elif (ticker.startswith('A') and ticker[1:].isdigit()) or ticker.endswith('.KS'):
        code = ticker[1:] + '.KS' if ticker.startswith('A') else ticker
    elif ' ' in ticker or 'Equity' in ticker:
        code = ticker.split(' ', 1)[0]
    else:
        code = ticker

    print(f"Ticker '{code}' loaded.")

    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')

    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            df = yf.download(code, start=start_date, end=end_date, progress=False)
    except Exception:
        return pd.Series(dtype=float)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    return df.get('Adj Close', df.get('Close')).dropna()

def get_daily_log_stats(series):
    log_ret = np.log(series / series.shift(1)).dropna()
    return log_ret.mean().item(), log_ret.std().item()

def compute_stats(input_source, periods,
                  output_file='output.xlsx',
                  trading_days=252,
                  ticker_col='Ticker',
                  name_col='Name'):
    df_in = load_input(input_source, ticker_col, name_col)
    today = datetime.today()
    earliest = (today - relativedelta(months=max(max(periods.values()), 60))).strftime('%Y-%m-%d')
    results = []

    for _, row in df_in.iterrows():
        tic, name = row['Ticker'], row['Name']
        res = {'Ticker': tic, 'Name': name}

        prices = fetch_price_series(tic, earliest)
        if prices.empty:
            for label in periods:
                res[f'avg_ret_{label}'] = np.nan
                res[f'vol_{label}']     = np.nan
            for y in [2022, 2023, 2024]:
                res[f'ret_{y}'] = np.nan
                res[f'vol_{y}'] = np.nan
        else:
            # 기간별 통계
            for label, m in periods.items():
                start = (today - relativedelta(months=m)).strftime('%Y-%m-%d')
                sub = prices.loc[start:]
                if sub.empty:
                    res[f'avg_ret_{label}'] = np.nan
                    res[f'vol_{label}']     = np.nan
                else:
                    mu, sigma = get_daily_log_stats(sub)
                    factor = trading_days * (m / 12)
                    res[f'avg_ret_{label}'] = mu * factor
                    res[f'vol_{label}']     = sigma * np.sqrt(factor)

                # ────── 샤프 비율 계산
                if sigma > 0:
                    rf = {'1m': rf_1m, '2m': rf_2m, '3m': rf_3m, '6m': rf_6m, '1y': rf_1y}.get(label, 0)
                    res[f'sharpe_{label}'] = (mu * factor - rf) / (sigma * (factor ** 0.5))
                else:
                    res[f'sharpe_{label}'] = np.nan

                # 새로 추가된 부분: 샤프 비율 계산
                res[f'sharpe_{label}'] = compute_sharpe_ratio(res[f'avg_ret_{label}'], res[f'vol_{label}'])
            # 연도별 통계
            for y in [2022, 2023, 2024]:
                suby = prices[prices.index.year == y]
                if suby.empty:
                    res[f'ret_{y}'], res[f'vol_{y}'] = np.nan, np.nan
                else:
                    mu, sigma = get_daily_log_stats(suby)
                    res[f'ret_{y}'] = mu * trading_days
                    res[f'vol_{y}'] = sigma * np.sqrt(trading_days)

        results.append(res)

    df_out = pd.DataFrame(results)
    for c in df_out.columns:
        if c not in ['Ticker', 'Name']:
            df_out[c] = df_out[c].astype(float)
    df_out.to_excel(output_file, index=False)
    print(f"Results saved to {output_file}.")