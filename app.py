import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import yfinance as yf
import pandas as pd
import riskfolio as rp
import warnings

warnings.filterwarnings("ignore")

app = dash.Dash(__name__, title="InvestPro - Riskfolio UI")

app.layout = html.Div(style={'backgroundColor': '#0b0e11', 'color': '#d1d4dc', 'fontFamily': 'sans-serif', 'minHeight': '100vh'}, children=[
    
    html.Div(style={'padding': '20px', 'borderBottom': '1px solid #2a2e39', 'textAlign': 'center'}, children=[
        html.H1("InvestPro - Portfolio Optimizer", style={'color': '#2196f3', 'margin': '0'})
    ]),

    html.Div(style={'display': 'flex'}, children=[
        
        # Sidebar
        html.Div(style={'width': '350px', 'padding': '20px', 'borderRight': '1px solid #2a2e39', 'backgroundColor': '#131722'}, children=[
            html.Label("Asset Tickers (es: AAPL, BTC-USD):", style={'fontWeight': 'bold'}),
            dcc.Input(id='input-tickers', value='SPY, TLT, GLD, AAPL, NVDA, BTC-USD', type='text', 
                     style={'width': '100%', 'backgroundColor': '#1e222d', 'color': 'white', 'border': '1px solid #2a2e39', 'padding': '10px', 'marginBottom': '20px', 'borderRadius': '4px'}),
            
            html.Label("Misura di Rischio:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='dropdown-rm', 
                         options=[
                             {'label': 'Varianza Classica (MV)', 'value': 'MV'},
                             {'label': 'Conditional VaR (CVaR)', 'value': 'CVaR'},
                             {'label': 'Max Drawdown (MDD)', 'value': 'MDD'}
                         ], value='MV', style={'color': 'black', 'marginBottom': '20px'}),
            
            html.Button("OTTIMIZZA PORTAFOGLIO", id='btn-optimize', n_clicks=0, 
                        style={'width': '100%', 'backgroundColor': '#2196f3', 'color': 'white', 'border': 'none', 'padding': '12px', 'fontWeight': 'bold', 'cursor': 'pointer', 'borderRadius': '4px'}),
            
            # Area Diagnostica
            html.Div(id='error-message', style={'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px'})
        ]),

        # Main Panel
        html.Div(style={'flex': '1', 'padding': '40px'}, children=[
            dcc.Loading(id="loading-output", children=[
                dcc.Graph(id='graph-weights', style={'height': '600px'})
            ], type="default", color="#2196f3")
        ])
    ])
])

@app.callback(
    [Output('graph-weights', 'figure'),
     Output('error-message', 'children'),
     Output('error-message', 'style')],
    Input('btn-optimize', 'n_clicks'),
    [State('input-tickers', 'value'),
     State('dropdown-rm', 'value')]
)
def update_portfolio(n_clicks, ticker_str, risk_measure):
    error_style = {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px', 'display': 'none'}
    
    if n_clicks == 0:
        return px.scatter(title="In attesa di input...").update_layout(template='plotly_dark'), "", error_style

    try:
        # 1. Parsing Tickers
        requested_tickers = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
        
        # 2. Download Dati
        # Scarichiamo i dati. yfinance gestisce internamente i fallimenti.
        raw_data = yf.download(requested_tickers, start="2020-01-01", end="2024-01-01", auto_adjust=True, progress=False)
        
        if raw_data.empty:
            error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350', 'border': '1px solid #ef5350'})
            return px.scatter().update_layout(template='plotly_dark'), "❌ Nessun dato scaricato. Controlla la connessione o i ticker.", error_style

        # 3. Estrazione Prezzi di Chiusura e Verifica "Vivi"
        # Se c'è un solo ticker, yfinance non crea un MultiIndex. Gestiamo entrambi i casi.
        if len(requested_tickers) > 1:
            prices = raw_data['Close']
        else:
            prices = raw_data['Close'].to_frame()
            prices.columns = requested_tickers

        # Identifichiamo quali colonne hanno effettivamente dei dati (non tutte NaN)
        valid_columns = prices.columns[prices.notna().any()].tolist()
        failed_tickers = list(set(requested_tickers) - set(valid_columns))
        
        if not valid_columns:
            error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350', 'border': '1px solid #ef5350'})
            return px.scatter().update_layout(template='plotly_dark'), f"❌ Tutti i ticker sono falliti: {failed_tickers}", error_style

        # 4. Calcolo Rendimenti solo sui validi
        # Usiamo l'intersezione delle date (dropna) solo per i ticker che hanno dati
        returns = prices[valid_columns].pct_change().dropna()

        if returns.empty:
            error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350', 'border': '1px solid #ef5350'})
            return px.scatter().update_layout(template='plotly_dark'), "❌ Dati storici comuni insufficienti tra gli asset selezionati.", error_style

        # 5. Logica di Ottimizzazione
        warning_msg = ""
        if failed_tickers:
            warning_msg = f"⚠️ Esclusi (senza dati): {', '.join(failed_tickers)}. "

        # Se abbiamo almeno 2 asset, usiamo Riskfolio
        if len(valid_columns) >= 2:
            port = rp.Portfolio(returns=returns)
            port.assets_stats(method_mu='hist', method_cov='hist')
            w = port.optimization(model='Classic', rm=risk_measure, obj='Sharpe', rf=0, l=0)
            w_df = w.reset_index()
            w_df.columns = ['Asset', 'Weight']
        else:
            # Se c'è un solo asset, il peso è forzatamente 100%
            w_df = pd.DataFrame({'Asset': valid_columns, 'Weight': [1.0]})
            warning_msg += "Solo un asset valido trovato: allocazione 100%."

        # 6. Creazione Grafico
        w_df['Weight %'] = w_df['Weight'] * 100
        fig = px.bar(w_df, x='Asset', y='Weight %', 
                     title=f"Allocazione Ottimale (Rischio: {risk_measure})",
                     text_auto='.2f', color='Weight %', color_continuous_scale='Blues')
        fig.update_layout(template='plotly_dark', paper_bgcolor='#0b0e11', plot_bgcolor='#0b0e11')
        
        # Gestione messaggi finali
        if warning_msg:
            error_style.update({'display': 'block', 'backgroundColor': 'rgba(255, 185, 0, 0.1)', 'color': '#ffb900', 'border': '1px solid #ffb900'})
            return fig, warning_msg, error_style
        
        error_style.update({'display': 'block', 'backgroundColor': 'rgba(76, 175, 80, 0.1)', 'color': '#4caf50', 'border': '1px solid #4caf50'})
        return fig, "✅ Ottimizzazione completata.", error_style

    except Exception as e:
        error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350', 'border': '1px solid #ef5350'})
        return px.scatter().update_layout(template='plotly_dark'), f"❌ Errore Tecnico: {str(e)}", error_style

if __name__ == '__main__':
    app.run(debug=True, port=5006)