import pandas as pd
import requests
from bs4 import BeautifulSoup
import io

def get_trending_assets():
    try:
        url = "https://finance.yahoo.com/markets/stocks/most-active/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        # BeautifulSoup uses lxml parser
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table')
        if table:
            df = pd.read_html(io.StringIO(str(table)))[0]
            df = df.iloc[:, [0, 1, 3, 4, 5]]
            df.columns = ['Ticker', 'Nome', 'Prezzo', 'Var', '% Var']
            return df.head(15).to_dict('records')
    except Exception as e:
        print(f"Discovery Error: {e}")
    return []