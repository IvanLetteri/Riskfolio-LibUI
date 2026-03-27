CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT,
    category TEXT,
    currency TEXT DEFAULT 'USD'
);

CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    date DATE NOT NULL,
    open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume INTEGER,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    UNIQUE(asset_id, date)
);

CREATE TABLE IF NOT EXISTS macro_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    series_id TEXT NOT NULL,
    date DATE NOT NULL,
    value REAL NOT NULL,
    UNIQUE(series_id, date)
);