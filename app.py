import dash
from ui.layouts import get_main_layout
import ui.callbacks 

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.layout = get_main_layout()

if __name__ == '__main__':
    app.run(debug=True, port=5006)