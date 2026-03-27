import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), 'investments.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

class DatabaseManager:
    def __init__(self):
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(DB_PATH)

    def init_db(self):
        with self.get_connection() as conn:
            with open(SCHEMA_PATH, 'r') as f:
                conn.executescript(f.read())

    def save_ohlcv(self, ticker, df):
        with self.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO assets (ticker) VALUES (?)", (ticker,))
            res = conn.execute("SELECT id FROM assets WHERE ticker = ?", (ticker,)).fetchone()
            asset_id = res[0]
            for date, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO prices (asset_id, date, open, high, low, close, adj_close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (asset_id, date.strftime('%Y-%m-%d'), row['Open'], row['High'], row['Low'], row['Close'], row['Close'], row['Volume']))
            conn.commit()

    def get_ohlcv(self, ticker):
        with self.get_connection() as conn:
            query = "SELECT p.date, p.open, p.high, p.low, p.close, p.volume FROM prices p JOIN assets a ON p.asset_id = a.id WHERE a.ticker = ? ORDER BY p.date ASC"
            df = pd.read_sql_query(query, conn, params=[ticker])
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df

    def save_macro_data(self, series_id, df):
        with self.get_connection() as conn:
            for date, row in df.iterrows():
                conn.execute("INSERT OR REPLACE INTO macro_data (series_id, date, value) VALUES (?, ?, ?)",
                            (series_id, date.strftime('%Y-%m-%d'), float(row.iloc[0])))
            conn.commit()

    def get_macro_data(self, series_id):
        with self.get_connection() as conn:
            query = "SELECT date, value FROM macro_data WHERE series_id = ? ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=[series_id])
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            return df