// static/js/chart.js

let historyChart = null;

/**
 * Load historical stock data and display chart and table
 * @param {string} symbol - Stock symbol
 * @param {string} period - Time period (1d, 5d, 1mo, 6mo, ytd, 1y, 3y, 5y, max)
 */
function loadStockHistory(symbol, period) {
    console.log('loadStockHistory called with symbol:', symbol, 'period:', period);
    const chartTitle = document.getElementById('chartTitle');
    if (!chartTitle) {
        console.error('chartTitle element not found');
        return;
    }
    
    chartTitle.innerText = `Loading data for ${symbol}...`;
    
    fetch(`/api/stock_history/${symbol}?period=${period}`)
        .then(response => {
            console.log('Fetch response status:', response.status);
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            if (!data.data || data.data.length === 0) {
                chartTitle.innerText = `No historical data available for ${symbol}`;
                return;
            }
            
            chartTitle.innerText = `Historical Price Movement - ${symbol} (${period.toUpperCase()})`;
            
            // Data is newest first from API, reverse for ascending chart
            const chartLabels = data.data.map(item => item.date).reverse();
            const chartData = data.data.map(item => item.close).reverse();
            
            createHistoryChart(chartLabels, chartData);
            updateMetrics(chartData); // Pass reversed chartData (oldest first) for metrics
            populateHistoryTable(data.data);
        })
        .catch(error => {
            console.error('Error loading stock history:', error);
            chartTitle.innerText = `Error loading data for ${symbol}: ${error.message}`;
        });
}

/**
 * Create or update the history chart
 * @param {Array} labels - Date labels (reversed to oldest first)
 * @param {Array} data - Price data (reversed to oldest first)
 */
function createHistoryChart(labels, data) {
    console.log('Creating chart with labels:', labels.length, 'data points:', data.length);
    const ctx = document.getElementById('historyChart')?.getContext('2d');
    if (!ctx) {
        console.error('historyChart canvas not found');
        return;
    }
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(30, 136, 229, 0.4)');
    gradient.addColorStop(1, 'rgba(30, 136, 229, 0.1)');
    
    const startPrice = data[0]; // Oldest price (leftmost on chart)
    const endPrice = data[data.length - 1]; // Newest price (rightmost on chart)
    const priceChange = endPrice - startPrice;
    const lineColor = priceChange >= 0 ? '#4CAF50' : '#F44336';
    
    if (historyChart) {
        historyChart.destroy();
    }
    
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Price',
                data: data,
                borderColor: lineColor,
                backgroundColor: gradient,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: lineColor,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#9e9e9e',
                        maxTicksLimit: 10
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: {
                        color: '#9e9e9e',
                        callback: function(value) {
                            return '₹' + value.toFixed(2);
                        }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return '₹' + context.parsed.y.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Update metrics based on chart data (oldest first, newest last)
 * @param {Array} chartData - Price data matching chart order
 */
function updateMetrics(chartData) {
    if (!chartData || chartData.length === 0) {
        const metrics = ['highPrice', 'lowPrice', 'avgPrice', 'priceChange'];
        metrics.forEach(id => {
            const elem = document.getElementById(id)?.querySelector('.metric-value');
            if (elem) elem.innerText = 'N/A';
        });
        return;
    }
    
    const highPrice = Math.max(...chartData);
    const lowPrice = Math.min(...chartData);
    const avgPrice = chartData.reduce((sum, price) => sum + price, 0) / chartData.length;
    const startPrice = chartData[0]; // Oldest price (leftmost on chart)
    const endPrice = chartData[chartData.length - 1]; // Newest price (rightmost on chart)
    const priceChange = endPrice - startPrice; // Newest - Oldest to match chart direction
    const percentChange = (priceChange / startPrice) * 100;
    
    const highPriceElem = document.getElementById('highPrice')?.querySelector('.metric-value');
    const lowPriceElem = document.getElementById('lowPrice')?.querySelector('.metric-value');
    const avgPriceElem = document.getElementById('avgPrice')?.querySelector('.metric-value');
    const changeElement = document.getElementById('priceChange')?.querySelector('.metric-value');
    
    if (highPriceElem) highPriceElem.innerText = '₹' + highPrice.toFixed(2);
    if (lowPriceElem) lowPriceElem.innerText = '₹' + lowPrice.toFixed(2);
    if (avgPriceElem) avgPriceElem.innerText = '₹' + avgPrice.toFixed(2);
    if (changeElement) {
        changeElement.innerText = `₹${priceChange.toFixed(2)} (${percentChange.toFixed(2)}%)`;
        changeElement.className = 'metric-value ' + (priceChange >= 0 ? 'up' : 'down');
    }
}

/**
 * Populate table with all historical data fields (newest first)
 * @param {Array} data - Historical data with all fields
 */
function populateHistoryTable(data) {
    console.log('Populating table with', data.length, 'rows');
    const tbody = document.querySelector('#historyTable tbody');
    if (!tbody) {
        console.error('historyTable tbody not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.date}</td>
            <td class="number">₹${item.open.toFixed(2)}</td>
            <td class="number">₹${item.high.toFixed(2)}</td>
            <td class="number">₹${item.low.toFixed(2)}</td>
            <td class="number">₹${item.close.toFixed(2)}</td>
            <td class="number">${item.volume.toLocaleString()}</td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Setup period selection dropdown
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Setting up period select');
    const periodSelect = document.getElementById('periodSelect');
    if (periodSelect && window.currentSymbol) {
        periodSelect.addEventListener('change', function() {
            console.log('Period changed to:', this.value);
            loadStockHistory(window.currentSymbol, this.value);
        });
    } else {
        console.error('periodSelect or currentSymbol not found');
    }
});x