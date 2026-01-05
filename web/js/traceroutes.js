// Traceroutes page JavaScript

let allTraceroutes = [];

// Load and display traceroutes
async function loadTraceroutes() {
    try {
        const limit = document.getElementById('limit-select').value;
        const response = await fetch(`/api/traceroutes?limit=${limit}`);
        const data = await response.json();

        if (data.success) {
            allTraceroutes = data.traceroutes;
            displayTraceroutes(allTraceroutes);
            updateStats();
        } else {
            showError('Failed to load traceroutes: ' + data.error);
        }
    } catch (error) {
        showError('Error loading traceroutes: ' + error.message);
    }
}

// Display traceroutes in table
function displayTraceroutes(traceroutes) {
    const tbody = document.getElementById('traceroutes-tbody');

    if (traceroutes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="no-data">No traceroutes found</td></tr>';
        return;
    }

    tbody.innerHTML = traceroutes.map(trace => {
        const fromName = trace.from_long_name || trace.from_short_name || trace.from_node_id;
        const toName = trace.to_long_name || trace.to_short_name || trace.to_node_id || 'Unknown';

        // Format route as short IDs with arrows
        const routePath = trace.route.map(nodeId => {
            // Extract last 4 chars of node ID
            return nodeId.slice(-4);
        }).join(' → ');

        // Format SNR data if available
        let signalQuality = 'N/A';
        if (trace.snr_data && trace.snr_data.length > 0) {
            const avgSnr = trace.snr_data.reduce((a, b) => a + b, 0) / trace.snr_data.length;
            const minSnr = Math.min(...trace.snr_data);
            const maxSnr = Math.max(...trace.snr_data);
            signalQuality = `Avg: ${avgSnr.toFixed(1)} dB (${minSnr.toFixed(1)} - ${maxSnr.toFixed(1)})`;
        }

        // Format timestamp
        const receivedDate = new Date(trace.received_at_utc);
        const receivedTime = formatRelativeTime(receivedDate);

        return `
            <tr>
                <td>${trace.id}</td>
                <td><strong>${fromName}</strong><br><small>${trace.from_node_id}</small></td>
                <td><strong>${toName}</strong><br><small>${trace.to_node_id || 'N/A'}</small></td>
                <td class="center">${trace.hop_count}</td>
                <td class="route-path"><code>${routePath}</code></td>
                <td class="center">${signalQuality}</td>
                <td>${receivedTime}<br><small>${receivedDate.toLocaleString()}</small></td>
            </tr>
        `;
    }).join('');
}

// Update statistics
function updateStats() {
    document.getElementById('stat-total-traceroutes').textContent = allTraceroutes.length;

    // Count unique routes (based on from-to pairs)
    const uniqueRoutes = new Set(allTraceroutes.map(t => `${t.from_node_id}-${t.to_node_id}`));
    document.getElementById('stat-unique-routes').textContent = uniqueRoutes.size;

    // Calculate average hops
    if (allTraceroutes.length > 0) {
        const avgHops = allTraceroutes.reduce((sum, t) => sum + t.hop_count, 0) / allTraceroutes.length;
        document.getElementById('stat-avg-hops').textContent = avgHops.toFixed(1);
    } else {
        document.getElementById('stat-avg-hops').textContent = '0';
    }
}

// Search filter
function filterTraceroutes() {
    const searchTerm = document.getElementById('search').value.toLowerCase();

    const filtered = allTraceroutes.filter(trace => {
        const fromName = (trace.from_long_name || trace.from_short_name || '').toLowerCase();
        const toName = (trace.to_long_name || trace.to_short_name || '').toLowerCase();
        const fromId = trace.from_node_id.toLowerCase();
        const toId = (trace.to_node_id || '').toLowerCase();
        const route = trace.route.join(' ').toLowerCase();

        return fromName.includes(searchTerm) ||
               toName.includes(searchTerm) ||
               fromId.includes(searchTerm) ||
               toId.includes(searchTerm) ||
               route.includes(searchTerm);
    });

    displayTraceroutes(filtered);
}

// Format relative time
function formatRelativeTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

// Show error message
function showError(message) {
    const tbody = document.getElementById('traceroutes-tbody');
    tbody.innerHTML = `<tr><td colspan="7" class="error">${message}</td></tr>`;
}

// Event listeners
document.getElementById('refresh-btn').addEventListener('click', loadTraceroutes);
document.getElementById('search').addEventListener('input', filterTraceroutes);
document.getElementById('limit-select').addEventListener('change', loadTraceroutes);

// Initial load
loadTraceroutes();

// Auto-refresh every 30 seconds
setInterval(loadTraceroutes, 30000);
