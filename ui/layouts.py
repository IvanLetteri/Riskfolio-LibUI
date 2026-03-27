from dash import dcc, html, dash_table

def get_sidebar():
    return html.Div(style={
        "position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "280px",
        "padding": "20px", "backgroundColor": "#131722", "borderRight": "1px solid #2a2e39", "zIndex": 1000
    }, children=[
        html.H2("InvestPro UI", style={'color': '#2196f3', 'marginBottom': '30px'}),
        html.Hr(style={'borderColor': '#2a2e39'}),
        dcc.Link("🎯 Optimization", href="/", style={'display': 'block', 'color': 'white', 'padding': '10px', 'textDecoration': 'none'}),
        dcc.Link("📈 Backtest", href="/backtest", style={'display': 'block', 'color': 'white', 'padding': '10px', 'textDecoration': 'none'}),
        dcc.Link("🔍 Scanner", href="/discovery", style={'display': 'block', 'color': 'white', 'padding': '10px', 'textDecoration': 'none'}),
        dcc.Link("🌍 Macro", href="/macro", style={'display': 'block', 'color': 'white', 'padding': '10px', 'textDecoration': 'none'}),
        html.Hr(style={'borderColor': '#2a2e39', 'marginTop': '20px'}),
        html.Label("Tickers:", style={'color': '#848e9c'}),
        dcc.Input(id='input-tickers', value='AAPL,MSFT,GLD,TLT,BTC-USD', type='text', style={'width': '100%', 'backgroundColor': '#1e222d', 'color': 'white'}),
        html.Label("Risk Measure:", style={'marginTop': '15px', 'display': 'block', 'color': '#848e9c'}),
        dcc.Dropdown(id='dropdown-rm', options=[
            {'label': 'Volatility (MV)', 'value': 'MV'},
            {'label': 'Conditional VaR (CVaR)', 'value': 'CVaR'},
            {'label': 'Max Drawdown (MDD)', 'value': 'MDD'}
        ], value='MV', style={'color': 'black'}),
        html.Button("RUN ANALYSIS", id='btn-run', n_clicks=0, style={'marginTop': '20px', 'width': '100%', 'backgroundColor': '#2196f3', 'color': 'white', 'border': 'none', 'padding': '10px'})
    ])

def get_main_layout():
    return html.Div(style={'backgroundColor': '#0b0e11', 'minHeight': '100vh'}, children=[
        dcc.Location(id='url', refresh=False),
        dcc.Store(id='store-data'),
        get_sidebar(),
        html.Div(style={"marginLeft": "300px", "padding": "30px"}, children=[
            html.Div(id='sec-opt', children=[
                html.H3("Portfolio Optimization Strategy", style={'color': '#2196f3'}),
                dcc.Graph(id='graph-frontier'),
                html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                    dcc.Graph(id='graph-weights', style={'flex': '1'}),
                    dcc.Graph(id='graph-risk', style={'flex': '1'})
                ])
            ]),
            html.Div(id='sec-back', children=[
                html.H3("Historical Performance Analysis", style={'color': '#2196f3'}),
                dcc.Graph(id='graph-equity'),
                dcc.Graph(id='graph-drawdown'),
                html.Div(id='backtest-metrics', style={'color': 'white', 'marginTop': '20px'})
            ], style={'display': 'none'}),
            html.Div(id='sec-disc', children=[
                html.H3("Market Scanner", style={'color': '#2196f3'}),
                html.Button("AVVIA SCANSIONE", id='btn-scan', n_clicks=0, style={'marginBottom': '20px'}),
                dash_table.DataTable(id='table-disc', style_header={'backgroundColor': '#111', 'color': '#848e9c'}, style_cell={'backgroundColor': '#131722', 'color': 'white'})
            ], style={'display': 'none'}),
            html.Div(id='sec-macro', children=[
                html.H3("Macro Context", style={'color': '#2196f3'}),
                html.Button("SYNC MACRO", id='btn-macro', n_clicks=0, style={'marginBottom': '20px'}),
                dcc.Graph(id='graph-macro')
            ], style={'display': 'none'})
        ])
    ])