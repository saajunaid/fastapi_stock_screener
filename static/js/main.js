// static/js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const resultsBody = document.getElementById('resultsBody');
    const signalFilter = document.getElementById('signalFilter');
    const profileFilter = document.getElementById('profileFilter');
    const frequencySelector = document.getElementById('frequencySelector');
    const statusBar = document.getElementById('statusBar');
    const progressBar = document.getElementById('progressBar');
    const themeToggle = document.getElementById('checkbox');
    const themeLabel = document.querySelector('.theme-label');

    let allResults = [];
    let currentFilters = { signal: '', profile: '' };

    function connectWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

        socket.onopen = () => fetchInitialData();
        socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'full_update') {
                allResults = message.data.results;
                updateStatus(message.data.status);
                updateTable();
                populateFilters();
            } else if (message.type === 'status' || message.type === 'progress') {
                updateStatus(message.data);
            }
        };
        socket.onclose = () => setTimeout(connectWebSocket, 3000);
        socket.onerror = (error) => { console.error("WebSocket error:", error); socket.close(); };
    }

    async function fetchInitialData() {
        try {
            const response = await fetch('/get_initial_data');
            const data = await response.json();
            allResults = data.results;
            updateStatus(data.status);
            updateTable();
            populateFilters();
        } catch (error) { console.error("Error fetching initial data:", error); }
    }

    function updateTable() {
        resultsBody.innerHTML = '';
        const filtered = allResults.filter(row => 
            (currentFilters.signal === '' || row.Signal.includes(currentFilters.signal)) &&
            (currentFilters.profile === '' || row.Profile === currentFilters.profile)
        );
        if (filtered.length === 0) {
            resultsBody.innerHTML = '<tr><td colspan="12" style="text-align:center;">No signals found.</td></tr>';
            return;
        }
        filtered.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${row.Symbol}</td><td>${row.TF}</td><td>${row.Price}</td><td>${row.Volume}</td><td>${row.VWMA}</td><td>${row.Stoch_k}</td><td>${row.Stoch_d}</td><td>${row.Signal}</td><td>${row.Candle}</td><td>${row.SL}</td><td>${row.TP}</td><td>${row.Profile}</td>`;
            resultsBody.appendChild(tr);
        });
    }

    function populateFilters() {
        const signals = [...new Set(allResults.map(r => r.Signal.split('(')[0].trim()))].filter(Boolean);
        const profiles = [...new Set(allResults.map(r => r.Profile))];
        const updateSelect = (select, options) => {
            const currentValue = select.value;
            while (select.options.length > 1) select.remove(1);
            options.sort().forEach(opt => select.add(new Option(opt, opt)));
            select.value = currentValue;
        };
        updateSelect(signalFilter, signals);
        updateSelect(profileFilter, profiles);
    }

    function updateStatus(status) {
        statusBar.textContent = `Status: ${status.status_message} | Last: ${status.last_scan} | Next: ${status.next_scan} | Auto: ${status.auto_run}`;
        progressBar.style.width = `${status.progress || 0}%`;
    }

    async function updateSchedule() {
        await fetch('/update_schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frequency: parseInt(frequencySelector.value, 10) }),
        });
    }

    function applyTheme(theme) {
        document.body.className = theme;
        themeToggle.checked = theme === 'dark-mode';
        themeLabel.textContent = theme === 'dark-mode' ? 'Light Mode' : 'Dark Mode';
    }

    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark-mode' : 'light-mode';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });
    
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => navigator.serviceWorker.register('/static/sw.js'));
    }

    signalFilter.addEventListener('change', (e) => { currentFilters.signal = e.target.value; updateTable(); });
    profileFilter.addEventListener('change', (e) => { currentFilters.profile = e.target.value; updateTable(); });
    frequencySelector.addEventListener('change', updateSchedule);

    const savedTheme = localStorage.getItem('theme') || 'light-mode';
    applyTheme(savedTheme);
    connectWebSocket();
});

