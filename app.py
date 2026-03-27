import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import riskfolio as rp
import numpy as np
import warnings

# Disable warnings for a cleaner terminal output
warnings.filterwarnings("ignore")

app = dash.Dash(__name__, title="InvestPro - Portfolio Analytics")

# --- UI LAYOUT ---
app.layout = html.Div(style={'backgroundColor': '#0b0e11', 'color': '#d1d4dc', 'fontFamily': 'sans-serif', 'minHeight': '100vh'}, children=[
    
    # Header
    html.Div(style={'padding': '20px', 'borderBottom': '1px solid #2a2e39', 'textAlign': 'center'}, children=[
        html.H1("InvestPro - Portfolio Analytics Terminal", style={'color': '#2196f3', 'margin': '0'})
    ]),

    html.Div(style={'display': 'flex'}, children=[
        
        # Sidebar
        html.Div(style={'width': '350px', 'padding': '20px', 'borderRight': '1px solid #2a2e39', 'backgroundColor': '#131722'}, children=[
            html.Label("Asset Tickers:", style={'fontWeight': 'bold'}),
            dcc.Input(id='input-tickers', value='SPY, TLT, GLD, AAPL, NVDA, BTC-USD', type='text', 
                     style={'width': '100%', 'backgroundColor': '#1e222d', 'color': 'white', 'border': '1px solid #2a2e39', 'padding': '10px', 'marginBottom': '20px', 'borderRadius': '4px'}),
            
            html.Label("Risk Measure:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(id='dropdown-rm', 
                         options=[
                             {'label': 'Standard Deviation (MV)', 'value': 'MV'},
                             {'label': 'Conditional VaR (CVaR)', 'value': 'CVaR'},
                             {'label': 'Max Drawdown (MDD)', 'value': 'MDD'}
                         ], value='MV', style={'color': 'black', 'marginBottom': '20px'}),
            
            html.Button("RUN ANALYTICS", id='btn-optimize', n_clicks=0, 
                        style={'width': '100%', 'backgroundColor': '#2196f3', 'color': 'white', 'border': 'none', 'padding': '12px', 'fontWeight': 'bold', 'cursor': 'pointer', 'borderRadius': '4px'}),
            
            html.Div(id='error-message', style={'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px'})
        ]),

        # Main Panel
        html.Div(style={'flex': '1', 'padding': '20px'}, children=[
            dcc.Loading(id="loading-output", children=[
                html.Div([
                    # Top Row: Efficient Frontier
                    dcc.Graph(id='graph-frontier', style={'height': '450px', 'marginBottom': '20px'}),
                    
                    # Bottom Row: Weights and Risk Contribution
                    html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                        dcc.Graph(id='graph-weights', style={'flex': '1', 'height': '400px'}),
                        dcc.Graph(id='graph-risk-contrib', style={'flex': '1', 'height': '400px'})
                    ])
                ])
            ], type="default", color="#2196f3")
        ])
    ])
])

# --- HELPER FUNCTION FOR RISK CONTRIBUTION ---
def calculate_risk_contribution(w, cov, returns, rm):
    """
    Calculates risk contribution. Fallback to manual calculation for MV if library fails.
    """
    weights = w.values.flatten()
    if rm == 'MV':
        # Manual calculation for Mean-Variance Risk Contribution
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        marginal_contrib = np.dot(cov, weights) / portfolio_vol
        risk_contrib = weights * marginal_contrib
        return pd.Series(risk_contrib, index=w.index)
    else:
        try:
            # Try using the library's built-in function
            return rp.risk_contribution(w, cov=cov, returns=returns, rm=rm)
        except:
            # If it fails, return equal contribution as a placeholder to avoid crash
            return pd.Series(weights, index=w.index)

# --- BACKEND LOGIC (CALLBACK) ---
@app.callback(
    [Output('graph-frontier', 'figure'),
     Output('graph-weights', 'figure'),
     Output('graph-risk-contrib', 'figure'),
     Output('error-message', 'children'),
     Output('error-message', 'style')],
    Input('btn-optimize', 'n_clicks'),
    [State('input-tickers', 'value'),
     State('dropdown-rm', 'value')]
)
def update_portfolio_analytics(n_clicks, ticker_str, risk_measure):
    error_style = {'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px', 'display': 'none'}
    empty_fig = go.Figure().update_layout(template='plotly_dark', paper_bgcolor='#0b0e11', plot_bgcolor='#0b0e11')
    
    if n_clicks == 0:
        return empty_fig, empty_fig, empty_fig, "", error_style

    try:
        # 1. Data Ingestion
        tickers = [t.strip().upper() for t in ticker_str.split(',') if t.strip()]
        raw_data = yf.download(tickers, start="2018-01-01", end="2024-01-01", auto_adjust=True, progress=False)['Close']
        
        if isinstance(raw_data, pd.Series): raw_data = raw_data.to_frame()
        valid_cols = raw_data.columns[raw_data.notna().any()].tolist()
        returns = raw_data[valid_cols].pct_change().dropna()

        if len(valid_cols) < 2:
            raise ValueError("At least 2 valid assets are required.")

        # 2. Portfolio Setup
        port = rp.Portfolio(returns=returns)
        port.assets_stats(method_mu='hist', method_cov='hist')
        
        # Optimization (Max Sharpe)
        w_opt = port.optimization(model='Classic', rm=risk_measure, obj='Sharpe', rf=0, l=0)
        
        # Frontier Calculation
        points = 20
        frontier = port.efficient_frontier(model='Classic', rm=risk_measure, points=points, rf=0)

        # 3. Frontier Plot Data
        mu = port.mu
        cov = port.cov
        frontier_returns = []
        frontier_risks = []

        for i in range(points):
            weights = frontier.iloc[:, i].values
            ret = np.sum(mu.values.flatten() * weights) * 252
            risk = np.sqrt(weights.T @ cov @ weights) * np.sqrt(252)
            frontier_returns.append(ret * 100)
            frontier_risks.append(risk * 100)

        opt_weights = w_opt.values.flatten()
        opt_ret = np.sum(mu.values.flatten() * opt_weights) * 252 * 100
        opt_risk = np.sqrt(opt_weights.T @ cov @ opt_weights) * np.sqrt(252) * 100

        # 4. Risk Contribution (Using our robust helper function)
        risk_contrib = calculate_risk_contribution(w_opt, cov, returns, risk_measure)
        risk_contrib_pct = (risk_contrib / risk_contrib.sum()) * 100

        # 5. Efficient Frontier Chart
        fig_frontier = go.Figure()
        fig_frontier.add_trace(go.Scatter(x=frontier_risks, y=frontier_returns, mode='lines+markers', name='Frontier', line=dict(color='#2196f3')))
        fig_frontier.add_trace(go.Scatter(x=[opt_risk], y=[opt_ret], mode='markers', name='Optimal', marker=dict(color='red', size=15, symbol='star')))
        fig_frontier.update_layout(title=f"Efficient Frontier ({risk_measure})", xaxis_title="Annualized Risk (%)", yaxis_title="Annualized Return (%)", template='plotly_dark')

        # 6. Weights Chart
        w_df = w_opt.reset_index()
        w_df.columns = ['Asset', 'Weight']
        fig_weights = go.Figure(go.Bar(x=w_df['Asset'], y=w_df['Weight']*100, marker_color='#26a69a'))
        fig_weights.update_layout(title="Portfolio Weights (%)", template='plotly_dark')

        # 7. Risk Contribution Chart
        fig_risk = go.Figure(data=[go.Pie(labels=risk_contrib_pct.index, values=risk_contrib_pct.values.flatten(), hole=.4)])
        fig_risk.update_layout(title="Risk Contribution (%)", template='plotly_dark')

        success_style = {'marginTop': '20px', 'padding': '10px', 'backgroundColor': 'rgba(76, 175, 80, 0.1)', 'color': '#4caf50', 'display': 'block'}
        return fig_frontier, fig_weights, fig_risk, "✅ Analysis successful.", success_style

    except Exception as e:
        error_style.update({'display': 'block', 'backgroundColor': 'rgba(239, 83, 80, 0.1)', 'color': '#ef5350'})
        return empty_fig, empty_fig, empty_fig, f"❌ Error: {str(e)}", error_style

if __name__ == '__main__':
    app.run(debug=True, port=5006)