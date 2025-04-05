// static/js/chart.js

/**
 * Load historical stock data and display chart
 * @param {string} symbol - Stock symbol
 * @param {string} period - Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)
 */
function loadStockHistory(symbol, period) {
    // Show loading state
    document.getElementById('chartTitle').innerText = `Loading data for ${symbol}...`;
    
    // Fetch stock history data
    fetch(`/api/stock_history/${symbol}?period=${period}`)
        .then(response => response.json())
        .then(data => {
            // Update chart title
            document.getElementById('chartTitle').innerText = `Historical Price Movement - ${symbol}`;
            
            // Prepare data for chart
            const chartLabels = data.data.map(item => item.date);
            const chartData = data.data.map(item => item.close);
            
            // Create or update chart
            createHistoryChart(chartLabels, chartData);
            
            // Update metrics
            updateMetrics(chartData);
        })
        .catch(error => {
            console.error('Error loading stock history:', error);
            document.getElementById('chartTitle').innerText = `Error loading data for ${symbol}`;
        });
}

/**
 * Create or update the history chart
 * @param {Array} labels - Date labels
 * @param {Array} data - Price data
 */
function createHistoryChart(labels, data) {
    // Get chart canvas
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    // Define gradient for chart
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(30, 136, 229, 0.4)');
    gradient.addColorStop(1, 'rgba(30, 136, 229, 0.1)');
    
    // Determine chart color based on price trend
    const startPrice = data[0];
    const endPrice = data[data.length - 1];
    const priceChange = endPrice - startPrice;
    const lineColor = priceChange >= 0 ? '#4CAF50' : '#F44336';
    
    // If chart already exists, destroy it first
    if (historyChart) {
        historyChart.destroy();
    }
    
    // Create new chart
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
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#9e9e9e',
                        maxTicksLimit: 10
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#9e9e9e',
                        callback: function(value) {
                            return '₹' + value;
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
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
 * Update metrics based on chart data
 * @param {Array} data - Price data
 */
function updateMetrics(data) {
    if (!data || data.length === 0) return;
    
    // Calculate metrics
    const highPrice = Math.max(...data);
    const lowPrice = Math.min(...data);
    const avgPrice = data.reduce((sum, price) => sum + price, 0) / data.length;
    
    const startPrice = data[0];
    const endPrice = data[data.length - 1];
    const priceChange = endPrice - startPrice;
    const percentChange = (priceChange / startPrice) * 100;
    
    // Update DOM
    document.getElementById('highPrice').querySelector('.metric-value').innerText = '₹' + highPrice.toFixed(2);
    document.getElementById('lowPrice').querySelector('.metric-value').innerText = '₹' + lowPrice.toFixed(2);
    document.getElementById('avgPrice').querySelector('.metric-value').innerText = '₹' + avgPrice.toFixed(2);
    
    const changeElement = document.getElementById('priceChange').querySelector('.metric-value');
    changeElement.innerText = `₹${priceChange.toFixed(2)} (${percentChange.toFixed(2)}%)`;
    changeElement.className = 'metric-value ' + (priceChange >= 0 ? 'up' : 'down');
}