from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_file
from utils.stock_data import get_stock_data, get_stocks_data, get_mutual_funds_data, find_and_test_mutual_funds, get_stock_history, get_upcoming_ipos, get_stock_dividends
import os
from datetime import datetime, timedelta
import pandas as pd
import io
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Default stocks list
DEFAULT_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "BAJFINANCE.NS",
    "SBIN.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ADANIENT.NS", "TATAMOTORS.NS"
]

# Tax rates for capital gains in India
TAX_RATES = {
    'short_term': 0.15,  # 15% for holdings less than 1 year
    'long_term': 0.10    # 10% for holdings more than 1 year (above ₹1 lakh exemption)
}
 
# Initialize session data
def initialize_session():
    if 'stocks' not in session:
        session['stocks'] = DEFAULT_STOCKS.copy()
    if 'portfolio' not in session:
        session['portfolio'] = []
    if 'sold_stocks' not in session:
        session['sold_stocks'] = []
    if 'alerts' not in session:
        session['alerts'] = []
    if 'dividends' not in session:
        session['dividends'] = []

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
        'company_name': stock.get('company_name', symbol),
        'quantity': quantity,
        'buy_price': stock['buy_price'],
        'sell_price': sell_price,
        'sell_date': datetime.now().strftime('%Y-%m-%d'),
        'buy_date': stock.get('purchase_date', 'Unknown'),
        'holding_period': calculate_holding_period(stock.get('purchase_date')),
        'profit_loss': pl,
        'tax_category': 'short_term' if calculate_holding_period(stock.get('purchase_date')) < 365 else 'long_term'
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

# NEW FEATURE: Portfolio diversification analysis
@app.route('/api/portfolio/diversification')
def portfolio_diversification():
    """Get portfolio diversification metrics"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    
    if not portfolio:
        return jsonify({
            'status': 'error',
            'message': 'Portfolio is empty'
        }), 400
    
    # Get current stock prices
    stocks_data = get_stocks_data([p['symbol'] for p in portfolio])
    for p in portfolio:
        stock = next((s for s in stocks_data if s['symbol'] == p['symbol']), None)
        if stock:
            p['current_price'] = stock['price']
    
    # Calculate total portfolio value
    total_value = sum(p['quantity'] * p['current_price'] for p in portfolio)
    
    # Calculate sector diversification
    sector_allocation = {}
    for p in portfolio:
        sector = p.get('sector', 'Unknown')
        stock_value = p['quantity'] * p['current_price']
        sector_allocation[sector] = sector_allocation.get(sector, 0) + stock_value
    
    # Calculate percentage allocation
    for sector in sector_allocation:
        sector_allocation[sector] = {
            'value': sector_allocation[sector],
            'percentage': (sector_allocation[sector] / total_value) * 100 if total_value > 0 else 0
        }
    
    # Calculate individual stock allocation
    stock_allocation = []
    for p in portfolio:
        stock_value = p['quantity'] * p['current_price']
        allocation_percentage = (stock_value / total_value) * 100 if total_value > 0 else 0
        stock_allocation.append({
            'symbol': p['symbol'],
            'name': p.get('company_name', p['symbol']),
            'value': stock_value,
            'percentage': allocation_percentage
        })
    
    # Sort by percentage (descending)
    stock_allocation.sort(key=lambda x: x['percentage'], reverse=True)
    
    # Calculate diversification score (more evenly distributed = higher score)
    num_stocks = len(portfolio)
    ideal_allocation = 100 / num_stocks if num_stocks > 0 else 0
    allocation_deviations = [abs(s['percentage'] - ideal_allocation) for s in stock_allocation]
    diversification_score = max(0, 100 - sum(allocation_deviations) / 2)  # Scale: 0 to 100
    
    concentration_risk = 'Low'
    if stock_allocation and stock_allocation[0]['percentage'] > 30:
        concentration_risk = 'High'
    elif stock_allocation and stock_allocation[0]['percentage'] > 20:
        concentration_risk = 'Medium'
    
    return jsonify({
        'status': 'success',
        'total_value': total_value,
        'sectors': sector_allocation,
        'stocks': stock_allocation,
        'metrics': {
            'num_sectors': len(sector_allocation),
            'num_stocks': num_stocks,
            'diversification_score': diversification_score,
            'concentration_risk': concentration_risk
        }
    })

# NEW FEATURE: Advanced Tax Calculator for capital gains
@app.route('/api/tax/calculate')
def calculate_taxes():
    """Calculate capital gains taxes based on portfolio and sold stocks"""
    initialize_session()
    sold_stocks = session.get('sold_stocks', [])
    
    if not sold_stocks:
        return jsonify({
            'status': 'success',
            'message': 'No sold stocks to calculate taxes',
            'tax_data': {
                'short_term': {
                    'total_gain': 0,
                    'tax_amount': 0
                },
                'long_term': {
                    'total_gain': 0,
                    'exempt_amount': 0,
                    'taxable_gain': 0,
                    'tax_amount': 0
                },
                'total_tax': 0
            }
        })
    
    # Group by tax category
    short_term_gains = [s for s in sold_stocks if s.get('tax_category') == 'short_term']
    long_term_gains = [s for s in sold_stocks if s.get('tax_category') == 'long_term']
    
    # Calculate short-term gains (taxed at 15%)
    short_term_total = sum(s['profit_loss'] for s in short_term_gains)
    short_term_tax = max(0, short_term_total * TAX_RATES['short_term'])
    
    # Calculate long-term gains (10% above 1 lakh exemption)
    long_term_total = sum(s['profit_loss'] for s in long_term_gains)
    # In India, exemption of ₹1,00,000 for long term capital gains
    exemption = 100000 
    long_term_taxable = max(0, long_term_total - exemption)
    long_term_tax = long_term_taxable * TAX_RATES['long_term']
    
    # Total tax liability
    total_tax = short_term_tax + long_term_tax
    
    tax_data = {
        'short_term': {
            'total_gain': short_term_total,
            'tax_rate': TAX_RATES['short_term'] * 100,
            'tax_amount': short_term_tax
        },
        'long_term': {
            'total_gain': long_term_total,
            'exempt_amount': min(exemption, long_term_total),
            'taxable_gain': long_term_taxable,
            'tax_rate': TAX_RATES['long_term'] * 100,
            'tax_amount': long_term_tax
        },
        'total_tax': total_tax,
        'financial_year': get_current_financial_year()
    }
    
    return jsonify({
        'status': 'success',
        'tax_data': tax_data,
        'sold_stocks': sold_stocks
    })

# NEW FEATURE: Portfolio historical performance chart
@app.route('/api/portfolio/history')
def portfolio_history():
    """Get historical performance data for the portfolio"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    
    if not portfolio:
        return jsonify({
            'status': 'error',
            'message': 'Portfolio is empty'
        }), 400
    
    # Get historical data for each stock
    combined_history = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Default to 1 year
    
    for stock in portfolio:
        symbol = stock['symbol']
        quantity = stock['quantity']
        purchase_date = stock.get('purchase_date')
        
        try:
            # Get historical data since purchase or last year
            history = get_stock_history(symbol, '1y')
            
            for _, row in history.iterrows():
                date = row['Date']
                if date not in combined_history:
                    combined_history[date] = {'date': date, 'value': 0}
                combined_history[date]['value'] += row['Close'] * quantity
        except Exception as e:
            print(f"Error getting history for {symbol}: {e}")
    
    # Convert to list and sort by date
    history_list = list(combined_history.values())
    history_list.sort(key=lambda x: x['date'])
    
    # Calculate performance metrics
    if history_list:
        current_value = history_list[-1]['value'] if history_list else 0
        initial_value = history_list[0]['value'] if history_list else 0
        value_change = current_value - initial_value
        percent_change = (value_change / initial_value * 100) if initial_value > 0 else 0
        
        # Calculate max drawdown
        max_drawdown = 0
        max_value = initial_value
        for item in history_list:
            max_value = max(max_value, item['value'])
            drawdown = (max_value - item['value']) / max_value if max_value > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        metrics = {
            'current_value': current_value,
            'initial_value': initial_value,
            'value_change': value_change,
            'percent_change': percent_change,
            'max_drawdown': max_drawdown * 100
        }
    else:
        metrics = {
            'current_value': 0,
            'initial_value': 0,
            'value_change': 0,
            'percent_change': 0,
            'max_drawdown': 0
        }
    
    return jsonify({
        'status': 'success',
        'history': history_list,
        'metrics': metrics
    })

# NEW FEATURE: Price Alerts
@app.route('/api/alerts')
def get_alerts():
    """Get all price alerts"""
    initialize_session()
    alerts = session.get('alerts', [])
    
    return jsonify({
        'status': 'success',
        'alerts': alerts
    })

@app.route('/add_alert', methods=['POST'])
def add_alert():
    """Add a new price alert"""
    symbol = request.form.get('symbol', '').strip().upper()
    price = request.form.get('price', type=float)
    alert_type = request.form.get('alert_type', '').lower()  # 'above' or 'below'
    
    if not symbol or not price or not alert_type or alert_type not in ['above', 'below']:
        return jsonify({'status': 'error', 'message': 'Invalid alert parameters'}), 400
    
    if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
        symbol = f"{symbol}.NS"
    
    # Get current price
    stock_data = get_stock_data(symbol)
    if not stock_data or stock_data.get('price') == 'Error':
        return jsonify({'status': 'error', 'message': 'Invalid stock symbol'}), 400
    
    current_price = stock_data['price']
    
    # Validate alert price based on type
    if alert_type == 'above' and price <= current_price:
        return jsonify({'status': 'error', 'message': 'Alert price must be above current price'}), 400
    elif alert_type == 'below' and price >= current_price:
        return jsonify({'status': 'error', 'message': 'Alert price must be below current price'}), 400
    
    # Create alert
    alerts = session.get('alerts', [])
    
    new_alert = {
        'id': str(datetime.now().timestamp()),
        'symbol': symbol,
        'name': stock_data.get('name', symbol),
        'price': price,
        'current_price': current_price,
        'type': alert_type,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'triggered': False
    }
    
    alerts.append(new_alert)
    session['alerts'] = alerts
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'message': f'Alert created for {symbol} when price goes {alert_type} ₹{price}',
        'alert': new_alert
    })

@app.route('/delete_alert', methods=['POST'])
def delete_alert():
    """Delete a price alert"""
    alert_id = request.form.get('id')
    
    if not alert_id:
        return jsonify({'status': 'error', 'message': 'No alert ID provided'}), 400
    
    alerts = session.get('alerts', [])
    original_length = len(alerts)
    alerts = [a for a in alerts if a.get('id') != alert_id]
    
    if len(alerts) == original_length:
        return jsonify({'status': 'error', 'message': 'Alert not found'}), 404
    
    session['alerts'] = alerts
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'message': 'Alert deleted successfully'
    })

@app.route('/check_alerts')
def check_alerts():
    """Check all alerts against current prices"""
    initialize_session()
    alerts = session.get('alerts', [])
    
    if not alerts:
        return jsonify({
            'status': 'success',
            'message': 'No alerts to check',
            'triggered': []
        })
    
    # Get current prices for all alert symbols
    symbols = list(set(a['symbol'] for a in alerts))
    stocks_data = get_stocks_data(symbols)
    
    # Check each alert
    triggered_alerts = []
    updated_alerts = []
    
    for alert in alerts:
        symbol = alert['symbol']
        stock = next((s for s in stocks_data if s['symbol'] == symbol), None)
        
        if not stock:
            updated_alerts.append(alert)
            continue
        
        current_price = stock['price']
        
        # Update current price in alert
        alert['current_price'] = current_price
        
        # Check if alert is triggered
        if (alert['type'] == 'above' and current_price >= alert['price']) or \
           (alert['type'] == 'below' and current_price <= alert['price']):
            alert['triggered'] = True
            alert['triggered_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            triggered_alerts.append(alert)
        
        updated_alerts.append(alert)
    
    # Update alerts in session
    session['alerts'] = updated_alerts
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'message': f'Checked {len(alerts)} alerts, {len(triggered_alerts)} triggered',
        'triggered': triggered_alerts
    })

# Helper function for calculating holding period
def calculate_holding_period(purchase_date_str):
    """Calculate holding period in days from purchase date to current date"""
    if not purchase_date_str or purchase_date_str == 'Unknown':
        return 0
    
    try:
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
        today = datetime.now()
        return (today - purchase_date).days
    except ValueError:
        return 0

# Helper function for getting current financial year
def get_current_financial_year():
    """Get current financial year in India format (YYYY-YY)"""
    today = datetime.now()
    if today.month < 4:  # Financial year in India runs from April to March
        return f"{today.year-1}-{str(today.year)[2:]}"
    else:
        return f"{today.year}-{str(today.year+1)[2:]}"

# NEW FEATURE: Dividend Tracking
@app.route('/api/dividends')
def get_dividends():
    """Get dividend information for portfolio stocks"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    dividends = session.get('dividends', [])
    
    if not portfolio:
        return jsonify({
            'status': 'success',
            'message': 'No stocks in portfolio',
            'dividends': dividends
        })
    
    # Get symbols from portfolio
    symbols = [stock['symbol'] for stock in portfolio]
    
    # Attempt to get dividend data for each stock
    for symbol in symbols:
        try:
            # Skip if we already have recent dividend data for this stock
            existing = next((d for d in dividends if d['symbol'] == symbol), None)
            if existing and (datetime.now() - datetime.strptime(existing['updated_at'], '%Y-%m-%d')).days < 30:
                continue
                
            dividend_data = get_stock_dividends(symbol)
            if dividend_data and not dividend_data.empty:
                # Filter last 12 months of dividends
                one_year_ago = datetime.now() - timedelta(days=365)
                recent_dividends = dividend_data[dividend_data.index >= one_year_ago]
                
                if not recent_dividends.empty:
                    # Calculate annual dividend yield and amount
                    stock_data = get_stock_data(symbol)
                    current_price = stock_data['price']
                    annual_dividend_amount = recent_dividends['Dividends'].sum()
                    dividend_yield = (annual_dividend_amount / current_price) * 100 if current_price > 0 else 0
                    
                    # Find portfolio quantity
                    stock_position = next((s for s in portfolio if s['symbol'] == symbol), None)
                    quantity = stock_position['quantity'] if stock_position else 0
                    dividend_income = annual_dividend_amount * quantity
                    
                    # Create or update dividend entry
                    if existing:
                        existing.update({
                            'annual_dividend': annual_dividend_amount,
                            'dividend_yield': dividend_yield,
                            'projected_income': dividend_income,
                            'last_dividend_date': recent_dividends.index.max().strftime('%Y-%m-%d') if not recent_dividends.empty else None,
                            'last_dividend_amount': recent_dividends['Dividends'].iloc[-1] if not recent_dividends.empty else 0,
                            'dividend_frequency': estimate_dividend_frequency(recent_dividends),
                            'history': recent_dividends.reset_index().to_dict('records'),
                            'updated_at': datetime.now().strftime('%Y-%m-%d')
                        })
                    else:
                        dividends.append({
                            'symbol': symbol,
                            'company_name': stock_data.get('name', symbol),
                            'annual_dividend': annual_dividend_amount,
                            'dividend_yield': dividend_yield,
                            'projected_income': dividend_income,
                            'last_dividend_date': recent_dividends.index.max().strftime('%Y-%m-%d') if not recent_dividends.empty else None,
                            'last_dividend_amount': recent_dividends['Dividends'].iloc[-1] if not recent_dividends.empty else 0,
                            'dividend_frequency': estimate_dividend_frequency(recent_dividends),
                            'history': recent_dividends.reset_index().to_dict('records'),
                            'updated_at': datetime.now().strftime('%Y-%m-%d')
                        })
        except Exception as e:
            print(f"Error fetching dividend data for {symbol}: {str(e)}")
    
    # Save to session
    session['dividends'] = dividends
    session.modified = True
    
    # Calculate summary metrics
    total_annual_income = sum(d.get('projected_income', 0) for d in dividends)
    average_yield = sum(d.get('dividend_yield', 0) for d in dividends) / len(dividends) if dividends else 0
    
    return jsonify({
        'status': 'success',
        'dividends': dividends,
        'metrics': {
            'total_stocks_with_dividends': len(dividends),
            'total_annual_income': total_annual_income,
            'average_yield': average_yield
        }
    })

def estimate_dividend_frequency(dividend_data):
    """Estimate dividend payment frequency based on historical data"""
    if dividend_data is None or dividend_data.empty or len(dividend_data) < 2:
        return "Unknown"
    
    # Calculate average days between dividends
    dates = sorted(dividend_data.index)
    if len(dates) < 2:
        return "Unknown"
    
    intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    avg_interval = sum(intervals) / len(intervals)
    
    # Determine frequency
    if avg_interval <= 40:  # Monthly
        return "Monthly"
    elif avg_interval <= 100:  # Quarterly
        return "Quarterly"
    elif avg_interval <= 200:  # Semi-annual
        return "Semi-annual"
    else:  # Annual
        return "Annual"

@app.route('/add_dividend', methods=['POST'])
def add_dividend():
    """Manually add dividend payment record"""
    symbol = request.form.get('symbol', '').strip().upper()
    amount = request.form.get('amount', type=float)
    payment_date = request.form.get('payment_date')  # Format: YYYY-MM-DD
    
    if not symbol or not amount or not payment_date:
        return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
    
    try:
        payment_date_obj = datetime.strptime(payment_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Initialize session
    initialize_session()
    dividends = session.get('dividends', [])
    portfolio = session.get('portfolio', [])
    
    # Check if stock is in portfolio
    stock_position = next((s for s in portfolio if s['symbol'] == symbol), None)
    if not stock_position:
        return jsonify({'status': 'error', 'message': 'Stock not in portfolio'}), 400
    
    # Get current stock data
    stock_data = get_stock_data(symbol)
    
    # Find or create dividend entry
    dividend_entry = next((d for d in dividends if d['symbol'] == symbol), None)
    
    if dividend_entry:
        # Update existing entry
        if 'history' not in dividend_entry:
            dividend_entry['history'] = []
        
        # Add new dividend record
        dividend_entry['history'].append({
            'Date': payment_date,
            'Dividends': amount
        })
        
        # Update metrics
        recent_history = [h for h in dividend_entry['history'] if 
                          datetime.strptime(h['Date'], '%Y-%m-%d') > datetime.now() - timedelta(days=365)]
        annual_dividend = sum(h['Dividends'] for h in recent_history)
        
        dividend_entry.update({
            'annual_dividend': annual_dividend,
            'dividend_yield': (annual_dividend / stock_data['price']) * 100 if stock_data['price'] > 0 else 0,
            'projected_income': annual_dividend * stock_position['quantity'],
            'last_dividend_date': payment_date,
            'last_dividend_amount': amount,
            'updated_at': datetime.now().strftime('%Y-%m-%d')
        })
    else:
        # Create new entry
        dividends.append({
            'symbol': symbol,
            'company_name': stock_data.get('name', symbol),
            'annual_dividend': amount,  # Initial annual is just this payment
            'dividend_yield': (amount / stock_data['price']) * 100 if stock_data['price'] > 0 else 0,
            'projected_income': amount * stock_position['quantity'],
            'last_dividend_date': payment_date,
            'last_dividend_amount': amount,
            'dividend_frequency': 'Unknown',  # Need more data to determine
            'history': [{
                'Date': payment_date,
                'Dividends': amount
            }],
            'updated_at': datetime.now().strftime('%Y-%m-%d')
        })
    
    # Save to session
    session['dividends'] = dividends
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'message': f'Added dividend of ₹{amount} for {symbol} on {payment_date}'
    })

@app.route('/dividends')
def dividends_page():
    """Render dividends tracking page"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    return render_template('dividends.html', portfolio=portfolio)

# NEW FEATURE: Portfolio Export Functionality
@app.route('/export_portfolio')
def export_portfolio():
    """Export portfolio data to CSV file"""
    initialize_session()
    portfolio = session.get('portfolio', [])
    
    if not portfolio:
        return jsonify({
            'status': 'error',
            'message': 'Portfolio is empty'
        }), 400
    
    # Get current prices
    symbols = [p['symbol'] for p in portfolio]
    stocks_data = get_stocks_data(symbols)
    
    # Update portfolio with current prices
    for p in portfolio:
        stock = next((s for s in stocks_data if s['symbol'] == p['symbol']), None)
        if stock:
            p['current_price'] = stock['price']
    
    # Create DataFrame
    portfolio_data = []
    for p in portfolio:
        current_value = p['quantity'] * p['current_price']
        cost_basis = p['quantity'] * p['buy_price']
        profit_loss = current_value - cost_basis
        profit_loss_pct = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
        
        portfolio_data.append({
            'Symbol': p['symbol'],
            'Company Name': p.get('company_name', p['symbol']),
            'Quantity': p['quantity'],
            'Buy Price': p['buy_price'],
            'Current Price': p['current_price'],
            'Buy Date': p.get('purchase_date', 'Unknown'),
            'Holding Period (Days)': calculate_holding_period(p.get('purchase_date')),
            'Current Value': current_value,
            'Cost Basis': cost_basis,
            'Profit/Loss': profit_loss,
            'Profit/Loss %': profit_loss_pct,
            'Sector': p.get('sector', 'Unknown')
        })
    
    # Convert to DataFrame and then to CSV
    df = pd.DataFrame(portfolio_data)
    csv_data = df.to_csv(index=False)
    
    # Create buffer for CSV file
    buffer = io.BytesIO()
    buffer.write(csv_data.encode('utf-8'))
    buffer.seek(0)
    
    # Generate filename with current date
    filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export_tax_report')
def export_tax_report():
    """Export capital gains tax report to CSV file"""
    initialize_session()
    sold_stocks = session.get('sold_stocks', [])
    
    if not sold_stocks:
        return jsonify({
            'status': 'error',
            'message': 'No sold stocks to generate tax report'
        }), 400
    
    # Create DataFrame
    tax_data = []
    for s in sold_stocks:
        holding_period = s.get('holding_period', 0)
        tax_category = 'Short-term' if holding_period < 365 else 'Long-term'
        tax_rate = TAX_RATES['short_term'] * 100 if tax_category == 'Short-term' else TAX_RATES['long_term'] * 100
        
        tax_data.append({
            'Symbol': s['symbol'],
            'Company Name': s.get('company_name', s['symbol']),
            'Quantity': s['quantity'],
            'Buy Price': s['buy_price'],
            'Sell Price': s['sell_price'],
            'Buy Date': s.get('buy_date', 'Unknown'),
            'Sell Date': s.get('sell_date', 'Unknown'),
            'Holding Period (Days)': holding_period,
            'Tax Category': tax_category,
            'Profit/Loss': s['profit_loss'],
            'Tax Rate (%)': tax_rate,
            'Estimated Tax': s['profit_loss'] * (TAX_RATES['short_term'] if tax_category == 'Short-term' else TAX_RATES['long_term']) if s['profit_loss'] > 0 else 0
        })
    
    # Convert to DataFrame and then to CSV
    df = pd.DataFrame(tax_data)
    csv_data = df.to_csv(index=False)
    
    # Create buffer for CSV file
    buffer = io.BytesIO()
    buffer.write(csv_data.encode('utf-8'))
    buffer.seek(0)
    
    # Generate filename with current date and financial year
    filename = f"tax_report_{get_current_financial_year()}.csv"
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/export_dividends')
def export_dividends():
    """Export dividend data to CSV file"""
    initialize_session()
    dividends = session.get('dividends', [])
    
    if not dividends:
        return jsonify({
            'status': 'error',
            'message': 'No dividend data to export'
        }), 400
    
    # Create DataFrame
    dividend_data = []
    for d in dividends:
        dividend_data.append({
            'Symbol': d['symbol'],
            'Company Name': d.get('company_name', d['symbol']),
            'Annual Dividend (₹)': d.get('annual_dividend', 0),
            'Dividend Yield (%)': d.get('dividend_yield', 0),
            'Projected Annual Income (₹)': d.get('projected_income', 0),
            'Last Dividend Date': d.get('last_dividend_date', 'Unknown'),
            'Last Dividend Amount (₹)': d.get('last_dividend_amount', 0),
            'Dividend Frequency': d.get('dividend_frequency', 'Unknown')
        })
    
    # Convert to DataFrame and then to CSV
    df = pd.DataFrame(dividend_data)
    csv_data = df.to_csv(index=False)
    
    # Create buffer for CSV file
    buffer = io.BytesIO()
    buffer.write(csv_data.encode('utf-8'))
    buffer.seek(0)
    
    # Generate filename with current date
    filename = f"dividend_report_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return send_file(
        buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True)