// Global variables
let stocks = [];
let autoRefreshInterval;
let refreshIntervalSeconds = 60; // Default refresh interval
let isAutoRefreshEnabled = true;
let sectorChart = null;
let ipoData = [];
let mutualFundsData = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupRefreshControls();
    setupModalInteractions();
    setupTableSorting();
    setupFilters();
    initializeSectorChart();
    
    fetchStockData();
    fetchIPOData();
    fetchMutualFundsData();
    startAutoRefresh();
}

function setupRefreshControls() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshInterval = document.getElementById('refreshInterval');
    const toggleAutoRefresh = document.getElementById('toggleAutoRefresh');
    
    refreshBtn.addEventListener('click', function() {
        fetchStockData();
    });
    
    refreshInterval.addEventListener('change', function() {
        refreshIntervalSeconds = parseInt(this.value);
        restartAutoRefresh();
    });
    
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

    const refreshFundsBtn = document.getElementById('refreshFundsBtn');
    if (refreshFundsBtn) {
        refreshFundsBtn.addEventListener('click', function() {
            fetchMutualFundsData();
        });
    }
    
    document.getElementById('resetWatchlist').addEventListener('click', function(e) {
        e.preventDefault();
        resetWatchlist();
    });
    
    const refreshIposBtn = document.getElementById('refreshIposBtn');
    if (refreshIposBtn) {
        refreshIposBtn.addEventListener('click', function() {
            fetchIPOData();
        });
    }
}

function setupModalInteractions() {
    const modal = document.getElementById('addStockModal');
    const addStockBtn = document.getElementById('addStockBtn');
    const closeBtn = modal.querySelector('.close');
    const cancelBtn = modal.querySelector('.modal-cancel');
    const addStockForm = document.getElementById('addStockForm');
    
    addStockBtn.addEventListener('click', function() {
        modal.style.display = 'block';
    });
    
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    cancelBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
    
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
    const fundFilter = document.getElementById('fundFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    
    stockFilter.addEventListener('input', filterStocks);
    trendFilter.addEventListener('change', filterStocks);
    if (fundFilter) fundFilter.addEventListener('input', filterFunds);
    if (categoryFilter) categoryFilter.addEventListener('change', filterFunds);
}

function fetchStockData() {
    updateStatus('Fetching stock data...');
    
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
            
            populateStockTable(stocks);
            updateLastUpdated(data.timestamp);
            updateMetrics(data.metrics);
            updateSectorChart(data.metrics.sector_distribution);
        })
        .catch(error => {
            console.error('Error fetching stock data:', error);
            updateStatus('Failed to fetch stock data. Please try again.');
        });
}

function fetchIPOData() {
    updateIPOStatus('Fetching upcoming IPO data...');
    
    fetch('/api/ipos')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateIPOStatus('');
            ipoData = data.data;
            populateIPOTable(ipoData);
        })
        .catch(error => {
            console.error('Error fetching IPO data:', error);
            updateIPOStatus('Failed to fetch IPO data. Please try again.');
        });
}

function fetchMutualFundsData() {
    updateFundsStatus('Fetching mutual fund data...');
    
    fetch('/api/mutualfunds')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateFundsStatus('');
            mutualFundsData = data.data;
            populateMutualFundsTable(mutualFundsData);
        })
        .catch(error => {
            console.error('Error fetching mutual fund data:', error);
            updateFundsStatus('Failed to fetch mutual fund data. Please try again.');
        });
}

function populateStockTable(stocks) {
    const tbody = document.querySelector('#stocksTable tbody');
    if (!tbody) return;
    
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
    
    document.querySelectorAll('.remove-stock').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            removeStock(symbol);
        });
    });
}

function populateIPOTable(ipos) {
    const tbody = document.querySelector('#iposTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (ipos.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="8" class="center">No upcoming IPOs available at this time</td>`;
        tbody.appendChild(row);
        return;
    }
    
    ipos.forEach(ipo => {
        const expectedDate = ipo.expected_date === 'TBA' ? 'TBA' : 
            new Date(parseInt(ipo.expected_date) * 1000).toLocaleDateString();
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ipo.company_name}</td>
            <td>${ipo.symbol}</td>
            <td>${ipo.price_range}</td>
            <td>${expectedDate}</td>
            <td>${ipo.issue_size}</td>
            <td>${ipo.lot_size}</td>
            <td>${ipo.sector}</td>
            <td><span class="badge ${ipo.status.toLowerCase()}">${ipo.status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function populateMutualFundsTable(funds) {
    const tbody = document.querySelector('#fundsTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (funds.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="7" class="center">No mutual fund data available</td>`;
        tbody.appendChild(row);
        return;
    }
    
    funds.forEach(fund => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${fund.name}</td>
            <td>${fund.category}</td>
            <td class="number ${fund.trend}">${fund.formatted.nav}</td>
            <td class="number ${fund.trend}">${fund.formatted.change_percent}</td>
            <td class="number">${fund.formatted.expense_ratio}</td>
            <td>${fund.risk_level}</td>
            <td class="number ${fund.return_1y >= 0 ? 'up' : 'down'}">${fund.return_1y !== undefined ? fund.return_1y.toFixed(2) + '%' : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateLastUpdated(timestamp) {
    document.getElementById('lastUpdated').textContent = timestamp;
}

function updateMetrics(metrics) {
    const totalValueElem = document.querySelector('#totalValue .metric-value');
    totalValueElem.textContent = `₹${(metrics.total_market_cap / 10000000).toFixed(2)}Cr`;
    
    const gainersCount = stocks.filter(stock => stock.trend === 'up').length;
    const losersCount = stocks.filter(stock => stock.trend === 'down').length;
    
    document.querySelector('#gainers .metric-value').textContent = gainersCount;
    document.querySelector('#losers .metric-value').textContent = losersCount;
}

function updateStatus(message) {
    const statusElem = document.getElementById('status');
    if (statusElem) statusElem.textContent = message;
}

function updateIPOStatus(message) {
    const statusElem = document.getElementById('ipoStatus');
    if (statusElem) statusElem.textContent = message;
}

function updateFundsStatus(message) {
    const statusElem = document.getElementById('fundsStatus');
    if (statusElem) statusElem.textContent = message;
}

function initializeSectorChart() {
    const sectorChartCtx = document.getElementById('sectorChart');
    if (!sectorChartCtx) return;
    
    sectorChart = new Chart(sectorChartCtx.getContext('2d'), {
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
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateSectorChart(sectorData) {
    if (!sectorChart) return;
    
    const labels = Object.keys(sectorData);
    const data = labels.map(label => sectorData[label]);
    
    sectorChart.data.labels = labels;
    sectorChart.data.datasets[0].data = data;
    sectorChart.update();
}

function sortTable(key, header) {
    const headers = document.querySelectorAll('#stocksTable th');
    headers.forEach(h => h.classList.remove('asc', 'desc'));
    
    let ascending = !header.classList.contains('asc');
    header.classList.toggle('asc', ascending);
    header.classList.toggle('desc', !ascending);
    
    stocks.sort((a, b) => {
        let valueA = a[key];
        let valueB = b[key];
        
        if (typeof valueA === 'number' && typeof valueB === 'number') {
            return ascending ? valueA - valueB : valueB - valueA;
        }
        
        valueA = String(valueA).toLowerCase();
        valueB = String(valueB).toLowerCase();
        
        return ascending ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA);
    });
    
    populateStockTable(stocks);
}

function filterStocks() {
    const filterText = document.getElementById('stockFilter').value.toLowerCase();
    const trendFilter = document.getElementById('trendFilter').value;
    
    const rows = document.querySelectorAll('#stocksTable tbody tr');
    
    rows.forEach(row => {
        const symbol = row.cells[0].textContent.toLowerCase();
        const name = row.cells[1].textContent.toLowerCase();
        const trend = row.querySelector('.number').classList.contains('up') ? 'up' : 
                      row.querySelector('.number').classList.contains('down') ? 'down' : 'neutral';
        
        const matchesText = symbol.includes(filterText) || name.includes(filterText);
        const matchesTrend = trendFilter === 'all' || trend === trendFilter;
        
        row.style.display = matchesText && matchesTrend ? '' : 'none';
    });
    
    const visibleRows = document.querySelectorAll('#stocksTable tbody tr:not([style*="display: none"])');
    updateStatus(visibleRows.length === 0 ? 'No stocks match the current filters' : '');
}

function filterFunds() {
    const filterText = document.getElementById('fundFilter')?.value.toLowerCase() || '';
    const categoryFilter = document.getElementById('categoryFilter')?.value || 'all';
    
    const rows = document.querySelectorAll('#fundsTable tbody tr');
    
    rows.forEach(row => {
        const name = row.cells[0].textContent.toLowerCase();
        const category = row.cells[1].textContent;
        
        const matchesText = name.includes(filterText);
        const matchesCategory = categoryFilter === 'all' || category === categoryFilter;
        
        row.style.display = matchesText && matchesCategory ? '' : 'none';
    });
    
    const visibleRows = document.querySelectorAll('#fundsTable tbody tr:not([style*="display: none"])');
    updateFundsStatus(visibleRows.length === 0 ? 'No funds match the current filters' : '');
}

function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(() => {
        fetchStockData();
        if (Math.floor(Date.now() / 1000) % (refreshIntervalSeconds * 5) < refreshIntervalSeconds) {
            fetchIPOData();
            fetchMutualFundsData();
        }
    }, refreshIntervalSeconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
}

function restartAutoRefresh() {
    stopAutoRefresh();
    if (isAutoRefreshEnabled) startAutoRefresh();
}

function addStockToWatchlist(stock) {
    updateStatus('Adding stock to watchlist...');
    
    const formData = new FormData();
    formData.append('stock', stock);
    
    fetch('/add_stock', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        updateStatus(data.message);
        if (data.status === 'success') fetchStockData();
    })
    .catch(error => {
        console.error('Error adding stock:', error);
        updateStatus('Failed to add stock. Please try again.');
    });
}

function removeStock(symbol) {
    updateStatus('Removing stock from watchlist...');
    
    const formData = new FormData();
    formData.append('stock', symbol);
    
    fetch('/remove_stock', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        updateStatus(data.message);
        if (data.status === 'success') fetchStockData();
    })
    .catch(error => {
        console.error('Error removing stock:', error);
        updateStatus('Failed to remove stock. Please try again.');
    });
}

function resetWatchlist() {
    updateStatus('Resetting watchlist...');
    
    fetch('/reset_watchlist', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        updateStatus(data.message);
        if (data.status === 'success') fetchStockData();
    })
    .catch(error => {
        console.error('Error resetting watchlist:', error);
        updateStatus('Failed to reset watchlist. Please try again.');
    });
}