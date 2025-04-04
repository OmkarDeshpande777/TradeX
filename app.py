from flask import Flask, render_template, jsonify, request
import requests
import pandas as pd
from datetime import datetime
import json

app = Flask(__name__)

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

def get_stock_data(symbol):
    """
    Get stock data directly from Yahoo Finance API
    """
    # Add .NS suffix if not already present
    if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
        symbol = f"{symbol}.NS"
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        # Extract the relevant data
        meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
        
        price = meta.get('regularMarketPrice', 'N/A')
        previous_close = meta.get('previousClose', 'N/A')
        
        if price != 'N/A' and previous_close != 'N/A':
            change = price - previous_close
            change_percent = (change / previous_close) * 100
        else:
            change = 'N/A'
            change_percent = 'N/A'
            
        return {
            'symbol': symbol,
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': meta.get('regularMarketVolume', 'N/A'),
            'name': meta.get('symbol', symbol)
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def get_indian_stocks_data(symbols):
    """
    Get data for multiple Indian stocks
    """
    all_data = []
    
    for symbol in symbols:
        print(f"Fetching data for {symbol}...")
        data = get_stock_data(symbol)
        
        if data:
            all_data.append(data)
        else:
            all_data.append({
                'symbol': symbol,
                'price': 'Error',
                'change': 'N/A',
                'change_percent': 'N/A',
                'volume': 'N/A',
                'name': symbol
            })
            
    return all_data

def format_indian_stocks_display(stocks_data):
    """
    Format the stocks data for display
    """
    formatted_data = []
    
    for stock in stocks_data:
        formatted_stock = stock.copy()
        
        if formatted_stock['price'] != 'Error' and formatted_stock['change'] != 'N/A':
            # Format change and change_percent
            if isinstance(formatted_stock['change'], (int, float)):
                formatted_stock['change_formatted'] = f"{formatted_stock['change']:+.2f}"
                formatted_stock['trend'] = 'up' if formatted_stock['change'] > 0 else ('down' if formatted_stock['change'] < 0 else 'neutral')
            else:
                formatted_stock['change_formatted'] = formatted_stock['change']
                formatted_stock['trend'] = 'neutral'
                
            if isinstance(formatted_stock['change_percent'], (int, float)):
                formatted_stock['change_percent_formatted'] = f"{formatted_stock['change_percent']:+.2f}%"
            else:
                formatted_stock['change_percent_formatted'] = formatted_stock['change_percent']
                
        else:
            formatted_stock['trend'] = 'neutral'
            formatted_stock['change_formatted'] = formatted_stock['change']
            formatted_stock['change_percent_formatted'] = formatted_stock['change_percent']
            
        formatted_data.append(formatted_stock)
        
    return formatted_data

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/stocks')
def get_stocks():
    """API endpoint to get stock data"""
    # Get stocks from query parameter or use defaults
    stocks_param = request.args.get('stocks')
    
    if stocks_param:
        stocks = stocks_param.split(',')
    else:   
        stocks = DEFAULT_STOCKS
    
    # Get data
    stocks_data = get_indian_stocks_data(stocks)
    formatted_data = format_indian_stocks_display(stocks_data)
    
    return jsonify({
        'data': formatted_data,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == "__main__":
    app.run(debug=True)