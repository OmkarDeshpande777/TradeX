// Global variables
let stocks = [];
let autoRefreshInterval;
let refreshIntervalSeconds = 60; // Default refresh interval
let isAutoRefreshEnabled = true;
let selectedStock = '';
let stockChart = null;
let sectorChart = null;

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize components
    setupRefreshControls();
    setupModalInteractions();
    setupTableSorting();
    setupFilters();
    initializeChartsWithoutData();
    
    // Load initial data
    fetchStockData();
    
    // Start auto-refresh
    startAutoRefresh();
}

function setupRefreshControls() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshInterval = document.getElementById('refreshInterval');
    const toggleAutoRefresh = document.getElementById('toggleAutoRefresh');
    
    // Setup refresh button
    refreshBtn.addEventListener('click', function() {
        fetchStockData();
    });
    
    // Setup refresh interval dropdown
    refreshInterval.addEventListener('change', function() {
        refreshIntervalSeconds = parseInt(this.value);
        restartAutoRefresh();
    });
    
    // Setup auto-refresh toggle
    toggleAutoRefresh.addEventListener('click', function() {
        if (isAutoRefreshEnabled) {
            stopAutoRefresh();
            this.textContent = 'Resume Auto-Refresh';
            this.classList.remove('secondary');
            this.classList.add('primary');
        } else {
            startAutoRefresh();
            this.textContent = 'Pause Auto-Refresh';
            this.classList.remove('primary');
            this.classList.add('secondary');
        }
        isAutoRefreshEnabled = !isAutoRefreshEnabled;
    });
    
    // Setup reset watchlist link
    document.getElementById('resetWatchlist').addEventListener('click', function(e) {
        e.preventDefault();
        resetWatchlist();
    });
}

function setupModalInteractions() {
    // Get modal elements
    const modal = document.getElementById('addStockModal');
    const addStockBtn = document.getElementById('addStockBtn');
    const closeBtn = modal.querySelector('.close');
    const cancelBtn = modal.querySelector('.modal-cancel');
    const addStockForm = document.getElementById('addStockForm');
    
    // Open modal on button click
    addStockBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    // Close modal on close button click
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // Close modal on cancel button click
    cancelBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
    
    // Handle form submission
    addStockForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const newStock = document.getElementById('newStock').value.trim();
        if (newStock) {
            addStockToWatchlist(newStock);
            document.getElementById('newStock').value = '';
            modal.style.display = 'none';
        }
    });
}

function setupTableSorting() {
    const table = document.getElementById('stocksTable');
    const headers = table.querySelectorAll('th[data-sort]');
    
    // Add click event to all sortable headers
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const sortKey = this.getAttribute('data-sort');
            sortTable(sortKey, this);
        });
    });
}

function setupFilters() {
    const stockFilter = document.getElementById('stockFilter');
    const trendFilter = document.getElementById('trendFilter');
    
    // Filter as you type
    stockFilter.addEventListener('input', filterStocks);
    
    // Filter on trend selection
    trendFilter.addEventListener('change', filterStocks);
}

// Data fetching functions
function fetchStockData() {
    updateStatus('Fetching stock data...');
    
    // Make API request to the server
    fetch('/api/stocks')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateStatus('');
            stocks = data.data;
            
            // Update the UI with the fetched data
            populateStockTable(stocks);
            updateLastUpdated(data.timestamp);
            updateMetrics(data.metrics);
            updateSectorChart(data.metrics.sector_distribution);
            
            // If a stock is selected, update its chart
            if (selectedStock) {
                loadStockHistory(selectedStock);
            }
        })
        .catch(error => {
            console.error('Error fetching stock data:', error);
            updateStatus('Failed to fetch stock data. Please try again.');
        });
}

function loadStockHistory(symbol) {
    // Fetch real historical data from the API
    fetch(`/api/stock_history/${symbol}?period=1y`)
        .then(response => response.json())
        .then(data => {
            const labels = data.data.map(item => item.date);
            const prices = data.data.map(item => item.close);
            updateStockChart(symbol, labels, prices);
        })
        .catch(error => {
            console.error('Error fetching stock history:', error);
            updateStatus('Failed to load stock history.');
        });
}

// UI update functions
function populateStockTable(stocks) {
    const tbody = document.querySelector('#stocksTable tbody');
    tbody.innerHTML = '';
    
    stocks.forEach(stock => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${stock.symbol}</td>
            <td>${stock.name}</td>
            <td class="number ${stock.trend}">${stock.formatted.price}</td>
            <td class="number ${stock.trend}">${stock.formatted.change}</td>
            <td class="number ${stock.trend}">${stock.formatted.change_percent}</td>
            <td class="number">${stock.formatted.volume}</td>
            <td>
                <div class="action-buttons">
                    <a href="/stock/${stock.symbol}/history" class="btn sm primary">History</a>
                    <button class="action-btn remove-stock" data-symbol="${stock.symbol}">❌</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Add event listeners for remove buttons
    document.querySelectorAll('.remove-stock').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            removeStock(symbol);
        });
    });
}

function updateLastUpdated(timestamp) {
    document.getElementById('lastUpdated').textContent = timestamp;
}

function updateMetrics(metrics) {
    // Update total market cap
    const totalValueElem = document.querySelector('#totalValue .metric-value');
    totalValueElem.textContent = `₹${(metrics.total_market_cap / 10000000).toFixed(2)}Cr`;
    
    // Update gainers and losers count
    const gainersCount = stocks.filter(stock => stock.trend === 'up').length;
    const losersCount = stocks.filter(stock => stock.trend === 'down').length;
    
    document.querySelector('#gainers .metric-value').textContent = gainersCount;
    document.querySelector('#losers .metric-value').textContent = losersCount;
}

function updateStatus(message) {
    document.getElementById('status').textContent = message;
}

function initializeChartsWithoutData() {
    // Initialize stock price chart
    const stockChartCtx = document.getElementById('stockChart').getContext('2d');
    stockChart = new Chart(stockChartCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Stock Price',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
    
    // Initialize sector distribution chart
    const sectorChartCtx = document.getElementById('sectorChart').getContext('2d');
    sectorChart = new Chart(sectorChartCtx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                    '#9966FF', '#FF9F40', '#2ECC71', '#E74C3C'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function updateStockChart(symbol, labels, prices) {
    // Update chart data
    stockChart.data.labels = labels;
    stockChart.data.datasets[0].data = prices;
    stockChart.data.datasets[0].label = `${symbol} Price`;
    stockChart.update();
}

function updateSectorChart(sectorData) {
    // Convert object to arrays for the chart
    const labels = Object.keys(sectorData);
    const data = labels.map(label => sectorData[label]);
    
    // Update chart data
    sectorChart.data.labels = labels;
    sectorChart.data.datasets[0].data = data;
    sectorChart.update();
}

// Data manipulation functions
function sortTable(key, header) {
    // Get all headers
    const headers = document.querySelectorAll('#stocksTable th');
    
    // Remove sorting classes from all headers
    headers.forEach(h => {
        h.classList.remove('asc', 'desc');
    });
    
    // Determine sort direction
    let ascending = true;
    if (header.classList.contains('asc')) {
        ascending = false;
        header.classList.remove('asc');
        header.classList.add('desc');
    } else {
        header.classList.add('asc');
    }
    
    // Sort the stocks array
    stocks.sort((a, b) => {
        let valueA = a[key];
        let valueB = b[key];
        
        // Handle numerical values
        if (typeof valueA === 'number' && typeof valueB === 'number') {
            return ascending ? valueA - valueB : valueB - valueA;
        }
        
        // Handle string values
        valueA = String(valueA).toLowerCase();
        valueB = String(valueB).toLowerCase();
        
        if (valueA < valueB) return ascending ? -1 : 1;
        if (valueA > valueB) return ascending ? 1 : -1;
        return 0;
    });
    
    // Update the table with sorted data
    populateStockTable(stocks);
}

function filterStocks() {
    const filterText = document.getElementById('stockFilter').value.toLowerCase();
    const trendFilter = document.getElementById('trendFilter').value;
    
    // Get all rows
    const rows = document.querySelectorAll('#stocksTable tbody tr');
    
    rows.forEach(row => {
        const symbol = row.cells[0].textContent.toLowerCase();
        const name = row.cells[1].textContent.toLowerCase();
        const trend = row.querySelector('.number').classList.contains('up') ? 'up' : 
                      row.querySelector('.number').classList.contains('down') ? 'down' : 'neutral';
        
        // Apply filters
        const matchesText = symbol.includes(filterText) || name.includes(filterText);
        const matchesTrend = trendFilter === 'all' || trend === trendFilter;
        
        // Show/hide row
        row.style.display = matchesText && matchesTrend ? '' : 'none';
    });
    
    // Update status message if no results
    const visibleRows = document.querySelectorAll('#stocksTable tbody tr:not([style*="display: none"])');
    if (visibleRows.length === 0) {
        updateStatus('No stocks match the current filters');
    } else {
        updateStatus('');
    }
}

// Auto-refresh functions
function startAutoRefresh() {
    // Clear any existing interval first
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Set new interval
    autoRefreshInterval = setInterval(fetchStockData, refreshIntervalSeconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

function restartAutoRefresh() {
    stopAutoRefresh();
    if (isAutoRefreshEnabled) {
        startAutoRefresh();
    }
}

// Server interaction functions
function addStockToWatchlist(stock) {
    updateStatus('Adding stock to watchlist...');
    
    // Create form data
    const formData = new FormData();
    formData.append('stock', stock);
    
    // Make POST request to add the stock
    fetch('/add_stock', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStatus(data.message);
            fetchStockData(); // Refresh data
        } else {
            updateStatus(data.message);
        }
    })
    .catch(error => {
        console.error('Error adding stock:', error);
        updateStatus('Failed to add stock. Please try again.');
    });
}

function removeStock(symbol) {
    updateStatus('Removing stock from watchlist...');
    
    // Create form data
    const formData = new FormData();
    formData.append('stock', symbol);
    
    // Make POST request to remove the stock
    fetch('/remove_stock', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStatus(data.message);
            fetchStockData(); // Refresh data
        } else {
            updateStatus(data.message);
        }
    })
    .catch(error => {
        console.error('Error removing stock:', error);
        updateStatus('Failed to remove stock. Please try again.');
    });
}

function resetWatchlist() {
    updateStatus('Resetting watchlist...');
    
    fetch('/reset_watchlist', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateStatus(data.message);
            fetchStockData(); // Refresh data
        } else {
            updateStatus(data.message);
        }
    })
    .catch(error => {
        console.error('Error resetting watchlist:', error);
        updateStatus('Failed to reset watchlist. Please try again.');
    });
}