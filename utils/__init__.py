# This file makes the utils directory a Python package
# It can be empty as it just indicates to Python that this directory should be treated as a package
# This allows you to use imports like: from utils.stock_data import get_stock_data

# You could also add initialization code here if needed
# For example, you could set up logging for the utils package:

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger for this package
logger = logging.getLogger('utils')

# You could also define package-level constants or configuration
VERSION = '1.0.0'