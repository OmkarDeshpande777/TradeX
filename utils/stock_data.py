import requests
import pandas as pd
from datetime import datetime, timedelta
import random
import time


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
        
        # Get additional information for enhanced display
        # Note: These are mock values since Yahoo Finance API may not provide all of them
        market_cap = price * random.randint(10000000, 1000000000) if isinstance(price, (int, float)) else 'N/A'
        volume = meta.get('regularMarketVolume', 'N/A')
        
        # Mock sector data (you can replace this with real data if available)
        sectors = ['Information Technology', 'Financial Services', 'Energy', 'Healthcare', 
                   'Consumer Goods', 'Industrial', 'Telecom', 'Utilities']
        sector = random.choice(sectors)
            
        return {
            'symbol': symbol,
            'name': meta.get('symbol', symbol).replace('.NS', '').replace('.BO', ''),
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': volume,
            'market_cap': market_cap,
            'sector': sector,
            'day_high': meta.get('dayHigh', price * 1.01 if isinstance(price, (int, float)) else 'N/A'),
            'day_low': meta.get('dayLow', price * 0.99 if isinstance(price, (int, float)) else 'N/A'),
            'trend': 'up' if (isinstance(change, (int, float)) and change > 0) else 
                     ('down' if (isinstance(change, (int, float)) and change < 0) else 'neutral'),
            'formatted': {
                'price': f"₹{price:.2f}" if isinstance(price, (int, float)) else price,
                'change': f"{change:+.2f}" if isinstance(change, (int, float)) else change,
                'change_percent': f"{change_percent:+.2f}%" if isinstance(change_percent, (int, float)) else change_percent,
                'market_cap': f"₹{market_cap/10000000:.2f}Cr" if isinstance(market_cap, (int, float)) else market_cap,
                'volume': f"{volume:,}" if isinstance(volume, (int, float)) else volume
            }
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {
            'symbol': symbol,
            'name': symbol.replace('.NS', '').replace('.BO', ''),
            'price': 'Error',
            'change': 'N/A',
            'change_percent': 'N/A',
            'volume': 'N/A',
            'market_cap': 'N/A',
            'sector': 'Unknown',
            'day_high': 'N/A',
            'day_low': 'N/A',
            'trend': 'neutral',
            'formatted': {
                'price': 'Error',
                'change': 'N/A',
                'change_percent': 'N/A',
                'market_cap': 'N/A',
                'volume': 'N/A'
            }
        }

def get_stocks_data(symbols):
    """
    Get data for multiple Indian stocks
    """
    all_data = []
    
    for symbol in symbols:
        print(f"Fetching data for {symbol}...")
        data = get_stock_data(symbol)
        
        if data:
            all_data.append(data)
    
    # Sort by market cap (descending)
    all_data.sort(key=lambda x: x['market_cap'] if isinstance(x['market_cap'], (int, float)) else 0, reverse=True)
            
    return all_data

def get_stock_history(symbol, days=30):
    """
    Get historical stock data (mocked for demonstration)
    """
    # This is a mock function - in production, you'd call Yahoo Finance API for historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    dates = []
    prices = []
    
    current_date = start_date
    # Start with a random price between 100 and 1000
    last_price = random.uniform(100, 1000)
    
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Only include weekdays
            dates.append(current_date.strftime('%Y-%m-%d'))
            # Generate a random price movement (-3% to +3% from previous day)
            price_change = last_price * random.uniform(-0.03, 0.03)
            last_price += price_change
            prices.append(round(last_price, 2))
        
        current_date += timedelta(days=1)
    
    return pd.DataFrame({
        'Date': dates,
        'Close': prices
    })
    
    # Update stock_data.py with real Yahoo Finance historical data function
    
# Keep existing functions and add:

def get_stock_history(symbol, period="1y"):
    """
    Get historical stock data from Yahoo Finance
    
    Parameters:
    symbol (str): Stock symbol
    period (str): Time period - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    
    Returns:
    pandas.DataFrame: Historical price data
    """
    # Add .NS suffix if not already present
    if not (symbol.endswith('.NS') or symbol.endswith('.BO')):
        symbol = f"{symbol}.NS"
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Get current time in Unix timestamp format
    now = int(time.time())
    
    # Set period
    period_seconds = {
        '1d': 86400,
        '5d': 432000,
        '1mo': 2592000,
        '3mo': 7776000,
        '6mo': 15552000,
        '1y': 31536000,
        '2y': 63072000,
        '5y': 157680000,
        'max': 9999999999
    }
    
    # Calculate start time based on period
    start_time = now - period_seconds.get(period, period_seconds['1y'])
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&period1={start_time}&period2={now}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return pd.DataFrame(columns=['Date', 'Close'])
            
        data = response.json()
        
        # Extract the relevant data
        result = data.get('chart', {}).get('result', [{}])[0]
        timestamps = result.get('timestamp', [])
        close_prices = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        
        # Convert timestamps to dates
        dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
        
        # Create DataFrame
        df = pd.DataFrame({
            'Date': dates,
            'Close': close_prices
        })
        
        # Clean up data - remove NaN values
        df = df.dropna()
        
        return df
        
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=['Date', 'Close'])