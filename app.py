import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import riskfolio as rp
import numpy as np
import warnings

warnings.filterwarnings("ignore")

app = dash.Dash(__name__, title="InvestPro - Portfolio Analytics")

app.layout = html.Div(style={'backgroundColor': '#0b0e11', 'color': '#d1d4dc', 'fontFamily': 'sans-serif', 'minHeight': '100vh'}, children=[
    
    html.Div(style={'padding': '20px', 'borderBottom': '1px solid #2a2e39', 'textAlign': 'center'}, children=[
        html.H1("InvestPro - Portfolio Analytics Terminal", style={'color': '#2196f3', 'margin': '0'})
    ]),

    html.Div(style={'display': 'flex'}, children=[
        
        # Sidebar
        html.Div(style={'width': '350px', 'padding': '20px', 'borderRight': '1px solid #2a2e39', 'backgroundColor': '#131722'}, children=[
            html.Label("Asset Tickers:", style={'fontWeight': 'bold'}),
            dcc.Input(id='input-tickers', value='SPY, TLT, GLD, AAPL, NVDA, BTC-USD', type='text', 
                     style={'width': '100%', 'backgroundColor': '#1e222d', 'color': 'white', 'border': '1px solid #2a2e39', 'padding': '10px', 'marginBottom': '20px', 'borderRadius': '4px'}),
            
            html.Label("Misura di Rischio:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='dropdown-rm', 
                         options=[
                             {'label': 'Varianza Classica (MV)', 'value': 'MV'},
                             {'label': 'Conditional VaR (CVaR)', 'value': 'CVaR'},
                             {'label': 'Max Drawdown (MDD)', 'value': 'MDD'}
                         ], value='MV', style={'color': 'black', 'marginBottom': '20px'}),
            
            html.Button("ANALIZZA FRONTIERA", id='btn-optimize', n_clicks=0, 
                        style={'width': '100%', 'backgroundColor': '#2196f3', 'color': 'white', 'border': 'none', 'padding': '12px', 'fontWeight': 'bold', 'cursor': 'pointer', 'borderRadius': '4px'}),
            
            html.Div(id='error-message', style={'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px'})
        ]),

        # Main Panel con due grafici
        html.Div(style={'flex': '1', 'padding': '20px'}, children=[
            dcc.Loading(id="loading-output", children=[
                html.Div([
                    # Grafico 1: Frontiera Efficiente
                    dcc.Graph(id='graph-frontier', style={'height': '450px', 'marginBottom': '20px'}),
                    # Grafico 2: Pesi del Portafoglio Ottimo
                    dcc.Graph(id='graph-weights', style={'height': '350px'})
                ])
            ], type="default", color="#2196f3")
        ])
    ])
])

@app.callback(
    [Output('graph-frontier', 'figure'),
     Output('graph-weights', 'figure'),
     Output('error-message', 'children'),
     Output('error-message', 'style')],
    Input('btn-optimize', 'n_clicks'),
    [State('input-tickers', 'value'),
     State('dropdown-rm', 'value')]
)
def update_analytics(n_clicks, ticker_str, risk_measure):
    error_style = {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px', 'display': 'none'}
    empty_fig = go.Figure().update_layout(template='plotly_dark')
    
    if n_clicks == 0:
        return empty_fig, empty_fig, "", error_style

    try:
        # 1. Download e Pulizia Dati
        requested_tickers = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
        raw_data = yf.download(requested_tickers, start="2018-01-01", end="2024-01-01", auto_adjust=True, progress=False)['Close']
        
        if isinstance(raw_data, pd.Series): raw_data = raw_data.to_frame()
        valid_cols = raw_data.columns[raw_data.notna().any()].tolist()
        returns = raw_data[valid_cols].pct_change().dropna()

        if len(valid_cols) < 2:
            raise ValueError("Servono almeno 2 asset validi per calcolare la frontiera.")

        # 2. Riskfolio Engine
        port = rp.Portfolio(returns=returns)
        port.assets_stats(method_mu='hist', method_cov='hist')
        
        # Calcolo Portafoglio Ottimo (Punto sulla curva)
        w_opt = port.optimization(model='Classic', rm=risk_measure, obj='Sharpe', rf=0, l=0)
        
        # Calcolo dell'intera Frontiera Efficiente (La curva)
        points = 20 # Numero di portafogli sulla curva
        frontier = port.efficient_frontier(model='Classic', rm=risk_measure, points=points, rf=0)

        # 3. Estrazione metriche per il grafico della Frontiera
        # Calcoliamo Rischio e Rendimento per ogni punto della frontiera
        mu = port.mu
        cov = port.cov
        returns_f = []
        risks_f = []

        for i in range(points):
            weights = frontier.iloc[:, i].values
            # Rendimento atteso annualizzato
            ret = np.sum(mu.values.flatten() * weights) * 252
            # Rischio (Volatilità) annualizzato
            risk = np.sqrt(weights.T @ cov @ weights) * np.sqrt(252)
            returns_f.append(ret * 100)
            risks_f.append(risk * 100)

        # Metriche del punto ottimo
        opt_weights = w_opt.values.flatten()
        opt_ret = np.sum(mu.values.flatten() * opt_weights) * 252 * 100
        opt_risk = np.sqrt(opt_weights.T @ cov @ opt_weights) * np.sqrt(252) * 100

        # 4. Creazione Grafico Frontiera (Scatter Plot)
        fig_frontier = go.Figure()
        # La curva
        fig_frontier.add_trace(go.Scatter(x=risks_f, y=returns_f, mode='lines+markers', name='Frontiera Efficiente', line=dict(color='#2196f3')))
        # Il punto ottimo
        fig_frontier.add_trace(go.Scatter(x=[opt_risk], y=[opt_ret], mode='markers', name='Portafoglio Ottimo (Max Sharpe)', marker=dict(color='red', size=15, symbol='star')))
        
        fig_frontier.update_layout(
            title=f"Frontiera Efficiente (Rischio: {risk_measure})",
            xaxis_title="Rischio Annualizzato (%)",
            yaxis_title="Rendimento Annualizzato (%)",
            template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722'
        )

        # 5. Creazione Grafico Pesi (Bar Chart)
        w_df = w_opt.reset_index()
        w_df.columns = ['Asset', 'Weight']
        fig_weights = go.Figure(go.Bar(x=w_df['Asset'], y=w_df['Weight']*100, marker_color='#26a69a'))
        fig_weights.update_layout(
            title="Composizione Portafoglio Ottimo",
            yaxis_title="Peso (%)",
            template='plotly_dark', paper_bgcolor='#131722', plot_bgcolor='#131722'
        )

        success_style = {'marginTop': '20px', 'padding': '10px', 'backgroundColor': 'rgba(76, 175, 80, 0.1)', 'color': '#4caf50', 'display': 'block'}
        return fig_frontier, fig_weights, "✅ Analisi completata.", success_style

    except Exception as e:
        error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350'})
        return empty_fig, empty_fig, f"❌ Errore: {str(e)}", error_style

if __name__ == '__main__':
    app.run(debug=True, port=5006)