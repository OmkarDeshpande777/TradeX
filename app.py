from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from utils.stock_data import get_stock_data, get_stocks_data, get_mutual_funds_data, find_and_test_mutual_funds, get_stock_history, get_upcoming_ipos
import os
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Default stocks list
DEFAULT_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "BAJFINANCE.NS",
    "SBIN.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ADANIENT.NS", "TATAMOTORS.NS"
]

# Initialize session data
def initialize_session():
    if 'stocks' not in session:
        session['stocks'] = DEFAULT_STOCKS.copy()
    if 'portfolio' not in session:
        session['portfolio'] = []
    if 'sold_stocks' not in session:
        session['sold_stocks'] = []  # Added for consistency with tax calculator

@app.route('/')
def index():
    """Render the main dashboard page"""
    initialize_session()
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
        
        # Portfolio summary for dashboard
        portfolio = session.get('portfolio', [])
        portfolio_value = sum(p['quantity'] * p['current_price'] for p in portfolio)
        portfolio_pl = sum(p['quantity'] * (p['current_price'] - p['buy_price']) for p in portfolio)
        
        return jsonify({
            'data': stocks_data,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'metrics': {
                'total_stocks': len(stocks_data),
                'total_market_cap': total_market_cap,
                'sector_distribution': sector_distribution,
                'portfolio_value': portfolio_value,
                'portfolio_pl': portfolio_pl
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
    session.modified = True
    return jsonify({'status': 'success', 'message': f'Added {stock} to watchlist'})

@app.route('/buy_stock', methods=['POST'])
def buy_stock():
    """Buy a stock and add to portfolio"""
    stock = request.form.get('stock', '').strip().upper()
    quantity = request.form.get('quantity', type=int)
    buy_price = request.form.get('buy_price', type=float)  # Optional manual price entry
    transaction_date = request.form.get('transaction_date')  # Format: YYYY-MM-DD
    transaction_type = request.form.get('transaction_type', 'buy').lower()  # 'buy' or 'average'
    notes = request.form.get('notes', '')  # Any additional notes about the transaction
    
    if not stock or not quantity or quantity <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid stock or quantity'}), 400
    
    if not (stock.endswith('.NS') or stock.endswith('.BO')):
        stock = f"{stock}.NS"
    
    # Get current stock data
    stock_data = get_stock_data(stock)
    if not stock_data or stock_data.get('price') == 'Error':
        return jsonify({'status': 'error', 'message': 'Invalid stock symbol'}), 400
    
    # Use provided price or current market price
    actual_buy_price = buy_price if buy_price else stock_data['price']
    
    # Format transaction date or use current date
    try:
        if transaction_date:
            formatted_date = datetime.strptime(transaction_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        else:
            formatted_date = datetime.now().strftime('%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Get portfolio and check if stock already exists
    portfolio = session.get('portfolio', [])
    existing_position = next((p for p in portfolio if p['symbol'] == stock), None)
    
    # Calculate transaction costs (example: 0.5% of transaction value)
    transaction_cost = round(actual_buy_price * quantity * 0.005, 2)
    total_cost = round(actual_buy_price * quantity + transaction_cost, 2)
    
    if existing_position and transaction_type == 'average':
        # Average down/up calculation
        total_shares = existing_position['quantity'] + quantity
        total_investment = (existing_position['quantity'] * existing_position['buy_price']) + (quantity * actual_buy_price)
        new_average_price = round(total_investment / total_shares, 2)
        
        # Update existing position
        existing_position['quantity'] = total_shares
        existing_position['buy_price'] = new_average_price
        existing_position['current_price'] = stock_data['price']
        existing_position['last_transaction_date'] = formatted_date
        
        # Append to transaction history if not present
        if 'transaction_history' not in existing_position:
            existing_position['transaction_history'] = []
        
        existing_position['transaction_history'].append({
            'date': formatted_date,
            'type': 'buy',
            'quantity': quantity,
            'price': actual_buy_price,
            'transaction_cost': transaction_cost,
            'notes': notes
        })
        
        message = f'Added {quantity} more shares of {stock} at ₹{actual_buy_price}. New average: ₹{new_average_price}'
    else:
        # New position
        new_position = {
            'symbol': stock,
            'company_name': stock_data.get('name', stock),
            'quantity': quantity,
            'buy_price': actual_buy_price,
            'current_price': stock_data['price'],
            'purchase_date': formatted_date,
            'last_transaction_date': formatted_date,
            'sector': stock_data.get('sector', 'Unknown'),
            'transaction_cost': transaction_cost,
            'total_cost': total_cost,
            'notes': notes,
            'transaction_history': [{
                'date': formatted_date,
                'type': 'buy',
                'quantity': quantity,
                'price': actual_buy_price,
                'transaction_cost': transaction_cost,
                'notes': notes
            }]
        }
        portfolio.append(new_position)
        message = f'Bought {quantity} shares of {stock} at ₹{actual_buy_price}'
    
    session['portfolio'] = portfolio
    session.modified = True
    
    return jsonify({
        'status': 'success', 
        'message': message,
        'details': {
            'symbol': stock,
            'quantity': quantity,
            'buy_price': actual_buy_price,
            'transaction_date': formatted_date,
            'transaction_cost': transaction_cost,
            'total_cost': total_cost
        }
    })

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
    period = request.args.get('period', '1y')
    try:
        history = get_stock_history(symbol, period)
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
        mutual_fund_info = find_and_test_mutual_funds()
        working_symbols = mutual_fund_info.get('working_symbols', [])
        
        if not working_symbols:
            return jsonify({
                'data': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'metrics': {'total_funds': 0},
                'message': 'No valid mutual fund symbols found'
            }), 200
        
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
        print(f"Error in /api/mutualfunds: {str(e)}")
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

@app.route('/portfolio')
def portfolio_page():
    """Render portfolio overview page"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    stocks_data = get_stocks_data([p['symbol'] for p in portfolio])
    for p in portfolio:
        stock = next((s for s in stocks_data if s['symbol'] == p['symbol']), None)
        if stock:
            p['current_price'] = stock['price']
    return render_template('portfolio.html', portfolio=portfolio)

@app.route('/tax_calculator')
def tax_calculator_page():
    """Render tax calculator page"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    sold_stocks = session.get('sold_stocks', [])  # Include sold stocks
    stocks_data = get_stocks_data([p['symbol'] for p in portfolio])
    for p in portfolio:
        stock = next((s for s in stocks_data if s['symbol'] == p['symbol']), None)
        if stock:
            p['current_price'] = stock['price']
    return render_template('tax_calculator.html', portfolio=portfolio, sold_stocks=sold_stocks)

@app.route('/money_management')
def money_management_page():
    """Render money management page"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    stocks_data = get_stocks_data([p['symbol'] for p in portfolio])
    for p in portfolio:
        stock = next((s for s in stocks_data if s['symbol'] == p['symbol']), None)
        if stock:
            p['current_price'] = stock['price']
    return render_template('money_management.html', portfolio=portfolio)

@app.route('/sell_stock', methods=['POST'])
def sell_stock():
    """Sell a stock from the portfolio"""
    symbol = request.form.get('symbol').upper()
    quantity = int(request.form.get('quantity', 1))
    trigger_price = float(request.form.get('trigger_price', 0))
    initialize_session()
    portfolio = session.get('portfolio', [])
    stock = next((p for p in portfolio if p['symbol'] == symbol), None)
    
    if not stock or stock['quantity'] < quantity:
        return jsonify({'status': 'error', 'message': 'Invalid stock or quantity'})
    
    stocks_data = get_stocks_data([symbol])
    current_price = stocks_data[0]['price'] if stocks_data else stock['current_price']
    
    if trigger_price > 0 and current_price < trigger_price:
        return jsonify({'status': 'pending', 'message': f'Sell order for {symbol} set at ₹{trigger_price}'})
    
    sell_price = current_price if trigger_price == 0 or current_price >= trigger_price else trigger_price
    sold_value = quantity * sell_price
    pl = (sell_price - stock['buy_price']) * quantity
    
    # Record sold stock
    session['sold_stocks'].append({
        'symbol': symbol,
        'quantity': quantity,
        'buy_price': stock['buy_price'],
        'sell_price': sell_price,
        'sell_date': datetime.now().strftime('%Y-%m-%d'),
        'profit_loss': pl
    })
    
    # Update portfolio
    if stock['quantity'] == quantity:
        portfolio.remove(stock)
    else:
        stock['quantity'] -= quantity
    session['portfolio'] = portfolio
    session['sold_stocks'] = session.get('sold_stocks', [])
    session.modified = True
    return jsonify({'status': 'success', 'message': f'Sold {quantity} shares of {symbol} at ₹{sell_price}'})

if __name__ == "__main__":
    app.run(debug=True)