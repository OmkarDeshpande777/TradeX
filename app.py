from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from utils.stock_data import get_stock_data, get_stocks_data, get_mutual_funds_data, find_and_test_mutual_funds
import os
from datetime import datetime, timedelta
from utils.stock_data import get_stock_history
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Default stocks list
DEFAULT_STOCKS = [
    "RELIANCE.NS",    # Reliance Industries
    "TCS.NS",         # Tata Consultancy Services
    "HDFCBANK.NS",    # HDFC Bank
    "INFY.NS",        # Infosys
    "BAJFINANCE.NS",  # Bajaj Finance
    "SBIN.NS",        # State Bank of India
    "ICICIBANK.NS",   # ICICI Bank
    "HINDUNILVR.NS",  # Hindustan Unilever
    "ADANIENT.NS",    # Adani Enterprises
    "TATAMOTORS.NS"   # Tata Motors
]

@app.route('/')
def index():
    """Render the main dashboard page"""
    # Initialize session if needed
    if 'stocks' not in session:
        session['stocks'] = DEFAULT_STOCKS
    
    return render_template('index.html', stocks=session['stocks'])

@app.route('/api/stocks')
def get_stocks():
    """API endpoint to get stock data"""
    # Get stocks from query parameter or use session stocks
    stocks_param = request.args.get('stocks')
    
    if stocks_param:
        stocks = stocks_param.split(',')
    else:
        stocks = session.get('stocks', DEFAULT_STOCKS)
    
    # Get data
    stocks_data = get_stocks_data(stocks)
    
    # Calculate portfolio metrics
    total_market_cap = sum(stock['market_cap'] for stock in stocks_data if isinstance(stock.get('market_cap'), (int, float)))
    
    # Group stocks by sector for distribution chart
    sector_distribution = {}
    for stock in stocks_data:
        sector = stock.get('sector', 'Unknown')
        if sector in sector_distribution:
            sector_distribution[sector] += 1
        else:
            sector_distribution[sector] = 1
    
    return jsonify({
        'data': stocks_data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'metrics': {
            'total_stocks': len(stocks_data),
            'total_market_cap': total_market_cap,
            'sector_distribution': sector_distribution
        }
    })

@app.route('/add_stock', methods=['POST'])
def add_stock():
    """Add a stock to the watchlist"""
    stock = request.form.get('stock', '').strip().upper()
    
    if not stock:
        return jsonify({'status': 'error', 'message': 'No stock symbol provided'}), 400
    
    # Add .NS suffix if not already present
    if not (stock.endswith('.NS') or stock.endswith('.BO')):
        stock = f"{stock}.NS"
    
    # Get current stocks
    current_stocks = session.get('stocks', DEFAULT_STOCKS.copy())
    
    # Check if stock already exists
    if stock in current_stocks:
        return jsonify({'status': 'error', 'message': 'Stock already in watchlist'}), 400
    
    # Validate the stock by attempting to fetch its data
    stock_data = get_stock_data(stock)
    if not stock_data or stock_data.get('price') == 'Error':
        return jsonify({'status': 'error', 'message': 'Invalid stock symbol'}), 400
    
    # Add to session
    current_stocks.append(stock)
    session['stocks'] = current_stocks
    
    return jsonify({'status': 'success', 'message': f'Added {stock} to watchlist'})

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    """Remove a stock from the watchlist"""
    stock = request.form.get('stock', '').strip()
    
    if not stock:
        return jsonify({'status': 'error', 'message': 'No stock symbol provided'}), 400
    
    # Get current stocks
    current_stocks = session.get('stocks', DEFAULT_STOCKS.copy())
    
    # Remove stock if it exists
    if stock in current_stocks:
        current_stocks.remove(stock)
        session['stocks'] = current_stocks
        return jsonify({'status': 'success', 'message': f'Removed {stock} from watchlist'})
    else:
        return jsonify({'status': 'error', 'message': 'Stock not in watchlist'}), 400

@app.route('/reset_watchlist', methods=['POST'])
def reset_watchlist():
    """Reset the watchlist to default stocks"""
    session['stocks'] = DEFAULT_STOCKS.copy()
    return jsonify({'status': 'success', 'message': 'Watchlist reset to defaults'})

@app.route('/api/stock_history/<symbol>')
def stock_history_api(symbol):
    """API endpoint to get historical stock data"""
    period = request.args.get('period', '1y')
    history = get_stock_history(symbol, period)
    
    # Convert DataFrame to list of dictionaries
    history_data = []
    for index, row in history.iterrows():
        history_data.append({
            'date': row['Date'],
            'close': row['Close']
        })
    
    return jsonify({
        'symbol': symbol,
        'period': period,
        'data': history_data
    })


working_symbols = find_and_test_mutual_funds()['working_symbols']

@app.route('/api/mutualfunds')
def get_mutual_funds():
    """API endpoint to get mutual fund data"""
    # Get mutual fund data using the working symbols
    funds_data = get_mutual_funds_data(working_symbols)
    
    if not funds_data:
        return jsonify({
            'data': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'No mutual fund data available at this time'
        })
    
    return jsonify({
        'data': funds_data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# Add a route for the history page view
@app.route('/stock/<symbol>/history')
def stock_history_page(symbol):
    """Render stock history page"""
    return render_template('stock_history.html', symbol=symbol)

@app.route('/api/ipos')
def get_ipos():
    """API endpoint to get upcoming IPO data"""
    from utils.stock_data import get_upcoming_ipos
    
    # Get IPO data
    ipos_data = get_upcoming_ipos()
    
    return jsonify({
        'data': ipos_data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == "__main__":
    app.run(debug=True)