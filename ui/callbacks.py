from dash import Input, Output, State, callback, html
import yfinance as yf
import pandas as pd
import json
import plotly.graph_objects as go
import numpy as np
from core.engine import QuantEngine
from scrapers.discovery import get_trending_assets
from scrapers.macro_data import sync_fred_data

@callback(
    [Output(f'sec-{i}', 'style') for i in ['opt', 'back', 'disc', 'macro']],
    [Input('url', 'pathname')]
)
def navigate(path):
    styles = [{'display': 'none'}] * 4
    if path == '/backtest': styles[1] = {'display': 'block'}
    elif path == '/discovery': styles[2] = {'display': 'block'}
    elif path == '/macro': styles[3] = {'display': 'block'}
    else: styles[0] = {'display': 'block'}
    return styles

@callback(
    [Output('store-data', 'data'), Output('backtest-metrics', 'children')],
    Input('btn-run', 'n_clicks'),
    [State('input-tickers', 'value'), State('dropdown-rm', 'value')]
)
def run_analysis(n, ticker_str, rm):
    if n == 0: return None, ""
    try:
        tickers = [t.strip().upper() for t in ticker_str.split(',')]
        df = yf.download(tickers, period="5y", auto_adjust=True, progress=False)['Close'].dropna()
        returns = df.pct_change().dropna()
        opt = QuantEngine.get_optimization_results(returns, rm)
        equity, dd, metrics = QuantEngine.get_backtest_results(returns, opt['weights'])
        
        mu_simple = opt['mu'].iloc[0].to_dict()
        data = {
            "weights": opt['weights'].to_dict()['weights'],
            "frontier": opt['frontier'].to_dict(),
            "risk_contrib": opt['risk_contrib'].to_dict(),
            "equity": {"x": equity.index.strftime('%Y-%m-%d').tolist(), "y": equity.values.tolist()},
            "drawdown": {"x": dd.index.strftime('%Y-%m-%d').tolist(), "y": dd.values.tolist()},
            "mu": mu_simple,
            "cov": opt['cov'].to_dict(),
            "rm": rm
        }
        met_html = [html.P(f"{k}: {v}", style={'fontSize': '18px', 'fontWeight': 'bold'}) for k, v in metrics.items()]
        return json.dumps(data), met_html
    except Exception as e:
        return None, f"Error: {str(e)}"

@callback(
    [Output('graph-frontier', 'figure'), Output('graph-weights', 'figure'), 
     Output('graph-risk', 'figure'), Output('graph-equity', 'figure'), 
     Output('graph-drawdown', 'figure')],
    [Input('store-data', 'data')]
)
def update_graphs(json_data):
    dark = {'template': 'plotly_dark', 'paper_bgcolor': '#0b0e11', 'plot_bgcolor': '#0b0e11'}
    if not json_data: return [go.Figure().update_layout(dark)] * 5
    data = json.loads(json_data)
    w = data['weights']
    frontier = pd.DataFrame(data['frontier'])
    mu = pd.Series(data['mu'])
    cov = pd.DataFrame(data['cov'])
    
    f_rets, f_risks = [], []
    for i in range(frontier.shape[1]):
        weights = frontier.iloc[:, i].values
        f_rets.append(np.sum(mu.values * weights) * 252 * 100)
        f_risks.append(np.sqrt(weights.T @ cov.values @ weights) * np.sqrt(252) * 100)
    
    fig_f = go.Figure(go.Scatter(x=f_risks, y=f_rets, mode='lines+markers', name='Frontier'))
    fig_f.update_layout(title="Efficient Frontier", **dark)
    fig_w = go.Figure(go.Bar(x=list(w.keys()), y=[v*100 for v in w.values()], marker_color='#26a69a'))
    fig_w.update_layout(title="Optimal Weights (%)", **dark)
    rc = data['risk_contrib']
    fig_rc = go.Figure(go.Pie(labels=list(rc.keys()), values=list(rc.values()), hole=.4))
    fig_rc.update_layout(title="Risk Contribution", **dark)
    fig_eq = go.Figure(go.Scatter(x=data['equity']['x'], y=data['equity']['y'], fill='tozeroy'))
    fig_eq.update_layout(title="Equity Curve", **dark)
    fig_dd = go.Figure(go.Scatter(x=data['drawdown']['x'], y=data['drawdown']['y'], fill='tozeroy', line=dict(color='red')))
    fig_dd.update_layout(title="Drawdown (%)", **dark)
    return fig_f, fig_w, fig_rc, fig_eq, fig_dd

@callback([Output('table-disc', 'data'), Output('table-disc', 'columns')], Input('btn-scan', 'n_clicks'))
def update_discovery(n):
    if not n: return [], []
    data = get_trending_assets()
    cols = [{"name": i, "id": i} for i in ['Ticker', 'Nome', 'Prezzo', 'Var', '% Var']]
    return data, cols

@callback(Output('graph-macro', 'figure'), Input('btn-macro', 'n_clicks'))
def update_macro(n):
    fig = go.Figure()
    for s in ['GS10', 'FEDFUNDS']:
        series = sync_fred_data(s)
        if not series.empty:
            fig.add_trace(go.Scatter(x=series.index, y=series.values, name=s))
    fig.update_layout(template='plotly_dark', title="Macro Yields", paper_bgcolor='#0b0e11', plot_bgcolor='#0b0e11')
    return fig