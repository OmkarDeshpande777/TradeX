from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from utils.stock_data import get_stock_data, get_stocks_data, get_mutual_funds_data, find_and_test_mutual_funds, get_stock_history, get_upcoming_ipos
import os
from datetime import datetime, timedelta
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
    if 'stocks' not in session:
        session['stocks'] = DEFAULT_STOCKS
    return render_template('index.html', stocks=session['stocks'])

@app.route('/api/stocks')
def get_stocks():
    """API endpoint to get stock data"""
    stocks_param = request.args.get('stocks')
    if stocks_param:
        stocks = stocks_param.split(',')
    else:
        stocks = session.get('stocks', DEFAULT_STOCKS)
    
    try:
        stocks_data = get_stocks_data(stocks)
        total_market_cap = sum(stock['market_cap'] for stock in stocks_data if isinstance(stock.get('market_cap'), (int, float)))
        sector_distribution = {}
        for stock in stocks_data:
            sector = stock.get('sector', 'Unknown')
            sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
        
        return jsonify({
            'data': stocks_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_stocks': len(stocks_data),
                'total_market_cap': total_market_cap,
                'sector_distribution': sector_distribution
            }
        })
    except Exception as e:
        return jsonify({
            'data': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {'error': str(e)},
            'message': 'Error fetching stock data'
        }), 500

@app.route('/add_stock', methods=['POST'])
def add_stock():
    """Add a stock to the watchlist"""
    stock = request.form.get('stock', '').strip().upper()
    if not stock:
        return jsonify({'status': 'error', 'message': 'No stock symbol provided'}), 400
    
    if not (stock.endswith('.NS') or stock.endswith('.BO')):
        stock = f"{stock}.NS"
    
    current_stocks = session.get('stocks', DEFAULT_STOCKS.copy())
    if stock in current_stocks:
        return jsonify({'status': 'error', 'message': 'Stock already in watchlist'}), 400
    
    stock_data = get_stock_data(stock)
    if not stock_data or stock_data.get('price') == 'Error':
        return jsonify({'status': 'error', 'message': 'Invalid stock symbol'}), 400
    
    current_stocks.append(stock)
    session['stocks'] = current_stocks
    session.modified = True  # Ensure session updates
    
    return jsonify({'status': 'success', 'message': f'Added {stock} to watchlist'})

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    """Remove a stock from the watchlist"""
    stock = request.form.get('stock', '').strip()
    if not stock:
        return jsonify({'status': 'error', 'message': 'No stock symbol provided'}), 400
    
    current_stocks = session.get('stocks', DEFAULT_STOCKS.copy())
    if stock in current_stocks:
        current_stocks.remove(stock)
        session['stocks'] = current_stocks
        session.modified = True
        return jsonify({'status': 'success', 'message': f'Removed {stock} from watchlist'})
    return jsonify({'status': 'error', 'message': 'Stock not in watchlist'}), 400

@app.route('/reset_watchlist', methods=['POST'])
def reset_watchlist():
    """Reset the watchlist to default stocks"""
    session['stocks'] = DEFAULT_STOCKS.copy()
    session.modified = True
    return jsonify({'status': 'success', 'message': 'Watchlist reset to defaults'})

@app.route('/api/stock_history/<symbol>')
def stock_history_api(symbol):
    """API endpoint to get historical stock data"""
    period = request.args.get('period', '1y')  # Default to 1 year
    try:
        history = get_stock_history(symbol, period)
        # Sort by index (date) in descending order
        history = history.sort_index(ascending=False)
        history_data = [
            {
                'date': row['Date'],
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            }
            for index, row in history.iterrows()
        ]
        return jsonify({
            'symbol': symbol,
            'period': period,
            'data': history_data
        })
    except Exception as e:
        return jsonify({
            'symbol': symbol,
            'period': period,
            'data': [],
            'message': f'Error fetching history: {str(e)}'
        }), 500

@app.route('/api/mutualfunds')
def get_mutual_funds():
    """API endpoint to get mutual fund data"""
    try:
        # Fetch and test mutual fund symbols
        mutual_fund_info = find_and_test_mutual_funds()
        working_symbols = mutual_fund_info.get('working_symbols', [])
        
        if not working_symbols:
            return jsonify({
                'data': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'metrics': {'total_funds': 0},
                'message': 'No valid mutual fund symbols found'
            }), 200
        
        # Get mutual fund data
        funds_data = get_mutual_funds_data(working_symbols)
        
        if not funds_data:
            return jsonify({
                'data': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'metrics': {'total_funds': 0},
                'message': 'Failed to fetch mutual fund data from source'
            }), 200
        
        return jsonify({
            'data': funds_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_funds': len(funds_data)
            }
        })
    except Exception as e:
        print(f"Error in /api/mutualfunds: {str(e)}")  # Log error to console
        return jsonify({
            'data': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {'error': str(e)},
            'message': 'Failed to fetch mutual fund data. Please try again.'
        }), 500

@app.route('/stock/<symbol>/history')
def stock_history_page(symbol):
    """Render stock history page"""
    return render_template('stock_history.html', symbol=symbol)

@app.route('/api/ipos')
def get_ipos():
    """API endpoint to get upcoming IPO data"""
    try:
        ipos_data = get_upcoming_ipos()
        return jsonify({
            'data': ipos_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_ipos': len(ipos_data)
            }
        })
    except Exception as e:
        return jsonify({
            'data': [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {'error': str(e)},
            'message': 'Error fetching IPO data'
        }), 500

if __name__ == "__main__":
    app.run(debug=True)