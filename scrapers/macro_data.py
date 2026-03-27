import yfinance as yf
import pandas as pd

def sync_fred_data(series_id):
    mapping = {'GS10': '^TNX', 'FEDFUNDS': '^IRX'}
    ticker = mapping.get(series_id, series_id)
    try:
        df = yf.download(ticker, period="5y", progress=False, auto_adjust=True)
        if not df.empty:
            return df['Close']
    except:
        pass
    return pd.Series()