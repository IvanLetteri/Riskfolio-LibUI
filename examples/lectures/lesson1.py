import yfinance as yf
import pandas as pd
import riskfolio as rp
import warnings

# Disabilitiamo i warning superflui per avere un output pulito
warnings.filterwarnings("ignore")

# 1. ACQUISIZIONE DATI REALI
tickers = ['SPY', 'TLT', 'GLD', 'AAPL', 'NVDA', 'BTC-USD']

print("📡 Scaricamento dati da Yahoo Finance...")
data = yf.download(tickers, start="2020-01-01", end="2024-01-01", auto_adjust=True)

# Estraiamo i prezzi di chiusura
data = data['Close']

# 2. CALCOLO DEI RENDIMENTI
# Risolviamo il FutureWarning di Pandas specificando fill_method=None
returns = data.pct_change().dropna()

# 3. INIZIALIZZAZIONE DELL'OGGETTO PORTFOLIO
port = rp.Portfolio(returns=returns)

# 4. STIMA DEI PARAMETRI
# Nota: rimosso il parametro 'd' perché per il metodo 'hist' (storico) 
# non è necessario. Il software userà i pesi uguali per tutto lo storico.
method_mu = 'hist' 
method_cov = 'hist' 
port.assets_stats(method_mu=method_mu, method_cov=method_cov)

# 5. OTTIMIZZAZIONE
model = 'Classic' 
rm = 'MV'         # MV = Mean-Variance (Varianza classica)
obj = 'Sharpe'    # Massimizziamo il rapporto Rendimento/Rischio
rf = 0            # Tasso risk-free
l = 0             # Fattore di avversione al rischio

# Calcolo dei pesi ottimali
w = port.optimization(model=model, rm=rm, obj=obj, rf=rf, l=l)

print("\n✅ MOTORE RISK-FOLIO ATTIVO")
print("Pesi Ottimali calcolati con successo:")
print(w.T) # Usiamo .T (trasposta) per leggerlo meglio in orizzontale