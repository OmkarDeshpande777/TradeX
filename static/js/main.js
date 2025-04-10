// Global variables
let stocks = [];
let autoRefreshInterval;
let refreshIntervalSeconds = 60;
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
    
    const refreshIposBtn = document.getElementById('refreshIposBtn');
    if (refreshIposBtn) {
        refreshIposBtn.addEventListener('click', function() {
            fetchIPOData();
        });
    }
}

function setupModalInteractions() {
    const addModal = document.getElementById('addStockModal');
    const buyModal = document.getElementById('buyStockModal');
    const addStockBtn = document.getElementById('addStockBtn');
    const addCloseBtn = addModal.querySelector('.close');
    const addCancelBtn = addModal.querySelector('.modal-cancel');
    const buyCloseBtn = buyModal.querySelector('.close');
    const buyCancelBtn = buyModal.querySelector('.modal-cancel');
    const addStockForm = document.getElementById('addStockForm');
    const buyStockForm = document.getElementById('buyStockForm');
    
    addStockBtn.addEventListener('click', function() {
        addModal.style.display = 'block';
    });
    
    addCloseBtn.addEventListener('click', function() {
        addModal.style.display = 'none';
    });
    
    addCancelBtn.addEventListener('click', function() {
        addModal.style.display = 'none';
    });
    
    buyCloseBtn.addEventListener('click', function() {
        buyModal.style.display = 'none';
    });
    
    buyCancelBtn.addEventListener('click', function() {
        buyModal.style.display = 'none';
    });
    
    window.addEventListener('click', function(event) {
        if (event.target == addModal) {
            addModal.style.display = 'none';
        }
        if (event.target == buyModal) {
            buyModal.style.display = 'none';
        }
    });
    
    addStockForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const newStock = document.getElementById('newStock').value.trim();
        if (newStock) {
            addStockToWatchlist(newStock);
            document.getElementById('newStock').value = '';
            addModal.style.display = 'none';
        }
    });
    
    buyStockForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const stock = document.getElementById('buySymbol').value;
        const quantity = document.getElementById('buyQuantity').value;
        const buyPrice = document.getElementById('buyPrice').value || '';
        const transactionDate = document.getElementById('transactionDate').value || '';
        const transactionType = document.getElementById('transactionType').value;
        const notes = document.getElementById('buyNotes').value;
        
        const formData = new FormData();
        formData.append('stock', stock);
        formData.append('quantity', quantity);
        if (buyPrice) formData.append('buy_price', buyPrice);
        if (transactionDate) formData.append('transaction_date', transactionDate);
        formData.append('transaction_type', transactionType);
        formData.append('notes', notes);
        
        fetch('/buy_stock', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            updateStatus(data.message);
            if (data.status === 'success') fetchStockData();
            buyModal.style.display = 'none';
        })
        .catch(error => {
            console.error('Error buying stock:', error);
            updateStatus('Failed to buy stock. Please try again.');
        });
    });
}

function setupTableSorting() {
    const headers = document.querySelectorAll('#stocksTable th[data-sort]');
    headers.forEach(header => {
        header.addEventListener('click', function() {
            const sortKey = this.getAttribute('data-sort');
            sortTable(sortKey, this);
        });
    });
}

function setupFilters() {
    // Filters are handled in index.html script block
}

function fetchStockData() {
    updateStatus('Fetching stock data...');
    
    fetch('/api/stocks')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            updateStatus('');
            stocks = data.data;
            populateStockTable(stocks);
            updateLastUpdated(data.timestamp);
            updateMetrics(data.metrics);
            updateSectorChart(data.metrics.sector_distribution);
            updatePortfolioSummary(data.metrics);
        })
        .catch(error => {
            console.error('Error fetching stock data:', error);
            updateStatus('Failed to fetch stock data. Please try again.');
        });
}

function populateStockTable(stocks) {
    const tbody = document.getElementById('stockTableBody');
    tbody.innerHTML = '';
    
    stocks.forEach(stock => {
        const row = document.createElement('tr');
        row.className = stock.trend === 'up' ? 'up' : (stock.trend === 'down' ? 'down' : 'neutral');
        row.innerHTML = `
            <td>${stock.symbol}</td>
            <td>${stock.name}</td>
            <td class="number">${stock.formatted.price}</td>
            <td class="number">${stock.formatted.change}</td>
            <td class="number">${stock.formatted.change_percent}</td>
            <td class="number">${stock.formatted.volume}</td>
            <td>
                <button class="btn sm primary buy-btn" data-symbol="${stock.symbol}">Buy</button>
                <button class="btn sm primary history-btn" data-symbol="${stock.symbol}">History</button>
                <button class="btn sm danger remove-btn" data-symbol="${stock.symbol}">Remove</button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    document.querySelectorAll('.buy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            document.getElementById('buySymbol').value = symbol;
            document.getElementById('buyStockModal').style.display = 'block';
        });
    });
    
    document.querySelectorAll('.history-btn').forEach(button => {
        button.addEventListener('click', function() {
            const symbol = this.getAttribute('data-symbol');
            window.location.href = `/stock/${symbol}/history`;
        });
    });
    
    document.querySelectorAll('.remove-btn').forEach(button => {
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
    // Removed totalValue, gainers, losers
}

function updatePortfolioSummary(metrics) {
    const portfolioValue = document.querySelector('#portfolioValue .metric-value');
    const portfolioPL = document.querySelector('#portfolioPL .metric-value');
    if (portfolioValue) portfolioValue.textContent = `₹${metrics.portfolio_value.toFixed(2)}`;
    if (portfolioPL) {
        portfolioPL.textContent = `₹${metrics.portfolio_pl.toFixed(2)}`;
        portfolioPL.className = 'metric-value ' + (metrics.portfolio_pl >= 0 ? 'up' : 'down');
    }
}

function updateStatus(message) {
    const status = document.getElementById('status');
    if (status) status.textContent = message;
}

function initializeSectorChart() {
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
    const labels = Object.keys(sectorData);
    const data = labels.map(label => sectorData[label]);
    sectorChart.data.labels = labels;
    sectorChart.data.datasets[0].data = data;
    sectorChart.update();
}

function sortTable(key, header) {
    const headers = document.querySelectorAll('#stocksTable th[data-sort]');
    headers.forEach(h => h.classList.remove('asc', 'desc'));
    
    let ascending = !header.classList.contains('asc');
    header.classList.toggle('asc', ascending);
    header.classList.toggle('desc', !ascending);
    
    stocks.sort((a, b) => {
        let valueA = a[key];
        let valueB = b[key];
        
        if (key === 'price' || key === 'change' || key === 'change_percent' || key === 'volume') {
            valueA = parseFloat(a.formatted[key].replace(/[₹%,]/g, '')) || 0;
            valueB = parseFloat(b.formatted[key].replace(/[₹%,]/g, '')) || 0;
            return ascending ? valueA - valueB : valueB - valueA;
        }
        
        valueA = String(valueA).toLowerCase();
        valueB = String(valueB).toLowerCase();
        
        return ascending ? valueA.localeCompare(valueB) : valueB.localeCompare(valueA);
    });
    
    populateStockTable(stocks);
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
    updateStatus(`Adding ${stock} to watchlist...`);
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

function fetchIPOData() {
    updateIPOStatus('Fetching upcoming IPO data...');
    fetch('/api/ipos')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
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
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${ipo.company_name}</td>
            <td>${ipo.symbol}</td>
            <td>${ipo.price_range}</td>
            <td>${ipo.expected_date}</td>
            <td>${ipo.issue_size}</td>
            <td>${ipo.lot_size}</td>
            <td>${ipo.sector}</td>
            <td><span class="badge ${ipo.status.toLowerCase()}">${ipo.status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function updateIPOStatus(message) {
    const statusElem = document.getElementById('ipoStatus');
    if (statusElem) statusElem.textContent = message;
}

function fetchMutualFundsData() {
    updateFundsStatus('Fetching mutual fund data...');
    fetch('/api/mutualfunds')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('Received mutual fund data:', data);
            updateFundsStatus('');
            mutualFundsData = data.data;
            populateMutualFundsTable(mutualFundsData);
        })
        .catch(error => {
            console.error('Error fetching mutual fund data:', error);
            updateFundsStatus('Failed to fetch mutual fund data. Please try again.');
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
            <td class="number ${fund.return_1y !== undefined && fund.return_1y >= 0 ? 'up' : 'down'}">${fund.return_1y !== undefined ? fund.return_1y.toFixed(2) + '%' : 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateFundsStatus(message) {
    const statusElem = document.getElementById('fundsStatus');
    if (statusElem) statusElem.textContent = message;
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

// Add these functions to main.js

function setupAdditionalInteractions() {
    // Export buttons (assuming added to index.html)
    document.getElementById('exportPortfolioBtn')?.addEventListener('click', () => window.location.href = '/export_portfolio');
    document.getElementById('exportTaxBtn')?.addEventListener('click', () => window.location.href = '/export_tax_report');
    document.getElementById('exportDividendsBtn')?.addEventListener('click', () => window.location.href = '/export_dividends');

    // Alerts modal (assuming added to index.html)
    const alertModal = document.getElementById('alertModal');
    const addAlertBtn = document.getElementById('addAlertBtn');
    const alertCloseBtn = alertModal?.querySelector('.close');
    const alertCancelBtn = alertModal?.querySelector('.modal-cancel');
    const alertForm = document.getElementById('alertForm');

    if (addAlertBtn && alertModal) {
        addAlertBtn.addEventListener('click', () => alertModal.style.display = 'block');
        alertCloseBtn.addEventListener('click', () => alertModal.style.display = 'none');
        alertCancelBtn.addEventListener('click', () => alertModal.style.display = 'none');
        window.addEventListener('click', (event) => {
            if (event.target == alertModal) alertModal.style.display = 'none';
        });

        alertForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const symbol = document.getElementById('alertSymbol').value;
            const price = document.getElementById('alertPrice').value;
            const alertType = document.getElementById('alertType').value;

            const formData = new FormData();
            formData.append('symbol', symbol);
            formData.append('price', price);
            formData.append('alert_type', alertType);

            fetch('/add_alert', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                updateStatus(data.message);
                if (data.status === 'success') fetchAlerts();
                alertModal.style.display = 'none';
            })
            .catch(error => {
                console.error('Error adding alert:', error);
                updateStatus('Failed to add alert');
            });
        });
    }
}

function fetchAlerts() {
    fetch('/api/alerts')
        .then(response => response.json())
        .then(data => {
            populateAlerts(data.alerts);
        })
        .catch(error => console.error('Error fetching alerts:', error));
}

function populateAlerts(alerts) {
    const alertList = document.getElementById('alertList');
    if (!alertList) return;
    alertList.innerHTML = '';
    alerts.forEach(alert => {
        const li = document.createElement('li');
        li.innerHTML = `
            ${alert.symbol}: ${alert.type} ₹${alert.price} (Current: ₹${alert.current_price}, ${alert.triggered ? 'Triggered' : 'Pending'})
            <button class="btn sm danger" onclick="deleteAlert('${alert.id}')">Delete</button>
        `;
        alertList.appendChild(li);
    });
}

function deleteAlert(alertId) {
    const formData = new FormData();
    formData.append('id', alertId);
    fetch('/delete_alert', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        updateStatus(data.message);
        if (data.status === 'success') fetchAlerts();
    })
    .catch(error => console.error('Error deleting alert:', error));
}

// Call this in initializeApp
function initializeApp() {
    setupRefreshControls();
    setupModalInteractions();
    setupAdditionalInteractions(); // Add this
    setupTableSorting();
    setupFilters();
    initializeSectorChart();
    
    fetchStockData();
    fetchIPOData();
    fetchMutualFundsData();
    fetchAlerts(); // Add this
    startAutoRefresh();
}