import requests
import pandas as pd
from datetime import datetime
import time
import json

def get_mutual_funds_data(fund_list=None, debug=False):
    """
    Get real-time mutual fund data from Yahoo Finance with improved error handling
    
    Parameters:
    fund_list (list): List of fund symbols. If None, uses default list
    debug (bool): If True, prints detailed debug information
    
    Returns:
    list: List of dictionaries containing mutual fund data
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Default mutual funds tickers if none provided
    if fund_list is None:
        fund_list = [
            'HDFC-TOP-100-FUND-DIRECT-PLAN-GROWTH.MF',
            'SBI-BLUECHIP-FUND-DIRECT-GROWTH.MF',
            'ICICI-PRU-BLUECHIP-FUND-DIRECT-PLAN-GROWTH.MF',
            'AXIS-BLUECHIP-FUND-DIRECT-GROWTH.MF',
            'MIRAE-ASSET-LARGE-CAP-FUND-DIRECT-PLAN-GROWTH.MF'
        ]
    
    mutual_funds_data = []
    
    # Loop through each fund individually for better error tracking
    for fund in fund_list:
        try:
            if debug:
                print(f"Processing fund: {fund}")
            
            # Get NAV and historical data
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{fund}?interval=1d"
            if debug:
                print(f"Fetching from URL: {chart_url}")
                
            chart_response = requests.get(chart_url, headers=headers)
            
            if chart_response.status_code != 200:
                if debug:
                    print(f"Error status code: {chart_response.status_code}")
                    print(f"Response: {chart_response.text}")
                continue
            
            chart_data = chart_response.json()
            
            # Check if we have actual results
            if not chart_data.get('chart', {}).get('result'):
                if debug:
                    print(f"No chart results for {fund}")
                    print(f"Response data: {json.dumps(chart_data)[:500]}...")
                continue
                
            meta = chart_data.get('chart', {}).get('result', [{}])[0].get('meta', {})
            
            if not meta:
                if debug:
                    print(f"No meta data for {fund}")
                continue
            
            # Get quote data
            quote_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={fund}"
            quote_response = requests.get(quote_url, headers=headers)
            
            quote = {}
            if quote_response.status_code == 200:
                quote_data = quote_response.json()
                quotes = quote_data.get('quoteResponse', {}).get('result', [])
                if quotes:
                    quote = quotes[0]
            
            # Extract NAV and changes
            nav = meta.get('regularMarketPrice')
            previous_nav = meta.get('previousClose')
            
            if nav is None:
                if debug:
                    print(f"No NAV data for {fund}")
                continue
                
            # Calculate changes
            if nav is not None and previous_nav is not None:
                change = nav - previous_nav
                change_percent = (change / previous_nav) * 100
            else:
                change = None
                change_percent = None
            
            # Get fund name
            fund_name = quote.get('longName') or quote.get('shortName') or meta.get('symbol', fund).replace('-', ' ').replace('.MF', '')
            
            # Try to determine category from name
            name_lower = fund_name.lower()
            if 'large cap' in name_lower:
                category = 'Large Cap'
            elif 'mid cap' in name_lower:
                category = 'Mid Cap'
            elif 'small cap' in name_lower:
                category = 'Small Cap'
            elif 'debt' in name_lower or 'bond' in name_lower:
                category = 'Debt'
            elif 'hybrid' in name_lower or 'balanced' in name_lower:
                category = 'Hybrid'
            elif 'index' in name_lower:
                category = 'Index'
            else:
                category = 'Equity'  # Default
            
            # Get historical data for calculating returns
            timestamps = chart_data.get('chart', {}).get('result', [{}])[0].get('timestamp', [])
            indicators = chart_data.get('chart', {}).get('result', [{}])[0].get('indicators', {})
            
            # Check if we have quote data with close prices
            if not indicators or 'quote' not in indicators or not indicators['quote'] or not indicators['quote'][0].get('close'):
                if debug:
                    print(f"No price history for {fund}")
                close_prices = []
            else:
                close_prices = indicators['quote'][0]['close']
            
            # Calculate returns if enough data points
            returns = {}
            if len(close_prices) > 250 and len(close_prices) == len(timestamps):  # Ensure data alignment
                valid_prices = [(ts, price) for ts, price in zip(timestamps, close_prices) if price is not None]
                
                if valid_prices:
                    latest_price = valid_prices[-1][1]
                    
                    # 1-year return
                    one_year_ago = int(time.time()) - 31536000
                    for ts, price in valid_prices:
                        if ts < one_year_ago:
                            returns['1y'] = ((latest_price / price) - 1) * 100
                            break
            
            # Get AUM and expense ratio
            aum = quote.get('totalAssets')
            expense_ratio = quote.get('yield')
            
            # Determine risk level based on category
            risk_level = 'Moderate'
            if category in ['Large Cap', 'Index', 'Debt']:
                risk_level = 'Low'
            elif category in ['Small Cap']:
                risk_level = 'High'
            
            fund_data = {
                'symbol': fund,
                'name': fund_name,
                'nav': nav,
                'change': change,
                'change_percent': change_percent,
                'category': category,
                'risk_level': risk_level,
                'expense_ratio': expense_ratio,
                'aum': aum,
                'return_1y': returns.get('1y'),
                'trend': 'up' if (change and change > 0) else ('down' if (change and change < 0) else 'neutral'),
                'formatted': {
                    'nav': f"₹{nav:.2f}" if nav is not None else 'N/A',
                    'change': f"{change:+.2f}" if change is not None else 'N/A',
                    'change_percent': f"{change_percent:+.2f}%" if change_percent is not None else 'N/A',
                    'expense_ratio': f"{expense_ratio}%" if expense_ratio is not None else 'N/A',
                    'aum': f"₹{aum/10000000:.2f} Cr" if aum is not None else 'N/A'
                }
            }
            
            mutual_funds_data.append(fund_data)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            if debug:
                print(f"Error processing mutual fund {fund}: {str(e)}")
            continue
    
    if not mutual_funds_data and debug:
        print("No mutual fund data retrieved. Check fund symbols and API access.")
        
    return mutual_funds_data

def test_mutual_fund_availability(fund_list=None):
    """
    Test if mutual fund data is available from Yahoo Finance
    
    Parameters:
    fund_list (list): List of fund symbols to test
    
    Returns:
    dict: Dictionary with test results
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Default mutual funds tickers if none provided or use common Indian Mutual Funds
    if fund_list is None:
        fund_list = [
            # Test with various formats to see which works
            'HDFC-TOP-100-FUND-DIRECT-PLAN-GROWTH.MF',
            '235467.BO',  # Some funds may be listed with numeric IDs
            'HDFC5OOFUNDREGU.NS',
            'ICICIPRUUS.BO',
            'LICMFINDEX.NS'
        ]
    
    results = {}
    
    for fund in fund_list:
        print(f"Testing fund: {fund}")
        
        # Test Chart API
        chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{fund}?interval=1d"
        chart_response = requests.get(chart_url, headers=headers)
        
        chart_status = chart_response.status_code
        chart_data = None
        if chart_status == 200:
            chart_data = chart_response.json()
        
        # Test Quote API
        quote_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={fund}"
        quote_response = requests.get(quote_url, headers=headers)
        
        quote_status = quote_response.status_code
        quote_data = None
        if quote_status == 200:
            quote_data = quote_response.json()
        
        # Store results
        results[fund] = {
            'chart_status': chart_status,
            'chart_has_data': chart_data is not None and 'chart' in chart_data and 'result' in chart_data['chart'] and len(chart_data['chart']['result']) > 0,
            'quote_status': quote_status,
            'quote_has_data': quote_data is not None and 'quoteResponse' in quote_data and 'result' in quote_data['quoteResponse'] and len(quote_data['quoteResponse']['result']) > 0
        }
        
        # Add a small delay
        time.sleep(0.5)
    
    return results

def get_indian_mutual_funds():
    """
    Attempt to find valid Indian mutual fund symbols by querying Yahoo Finance API
    
    Returns:
    list: List of found mutual fund symbols
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Try different search terms for Indian mutual funds
    search_terms = [
        "HDFC Mutual Fund",
        "ICICI Prudential Mutual Fund",
        "SBI Mutual Fund",
        "Axis Mutual Fund",
        "Kotak Mutual Fund"
    ]
    
    fund_symbols = []
    
    for term in search_terms:
        try:
            # Encode the search term for URL
            encoded_term = requests.utils.quote(term)
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded_term}&quotesCount=10&newsCount=0"
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', [])
                
                for quote in quotes:
                    symbol = quote.get('symbol')
                    if symbol and (symbol.endswith('.MF') or symbol.endswith('.BO') or symbol.endswith('.NS')):
                        fund_symbols.append(symbol)
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error searching for {term}: {str(e)}")
    
    return fund_symbols

def find_and_test_mutual_funds():
    """
    Find and test Indian mutual fund symbols
    
    Returns:
    dict: Results of tests and list of working symbols
    """
    print("Searching for Indian mutual funds...")
    symbols = get_indian_mutual_funds()
    
    if not symbols:
        print("No mutual fund symbols found through search.")
        # Try some default symbols in various formats
        symbols = [
            'HDFCTO-DP.BO',
            'AXISGR.BO',
            'LICMFGII.NS',
            'TATADIVA.BO',
            'BSLNIFTY.NS'
        ]
    
    print(f"Found {len(symbols)} symbols. Testing availability...")
    results = test_mutual_fund_availability(symbols)
    
    working_symbols = []
    for symbol, result in results.items():
        if result['chart_has_data'] or result['quote_has_data']:
            working_symbols.append(symbol)
    
    return {
        'test_results': results,
        'working_symbols': working_symbols
    }
    
result = find_and_test_mutual_funds()
print(f"Working symbols: {result['working_symbols']}")

data = get_mutual_funds_data(result['working_symbols'], debug=True)
print(data)