// Node Connections page JavaScript

let allNodes = [];
let allTopology = [];
let nodeConnections = new Map();

// Load nodes and topology data
async function loadData() {
    try {
        // Load nodes
        const nodesResponse = await fetch('/api/nodes');
        const nodesData = await nodesResponse.json();

        // Load topology
        const topologyResponse = await fetch('/api/topology?active_only=true');
        const topologyData = await topologyResponse.json();

        if (nodesData.success && topologyData.success) {
            allNodes = nodesData.nodes;
            allTopology = topologyData.links;
            processConnections();
            displayConnections();
            updateStats();
        } else {
            showError('Failed to load data');
        }
    } catch (error) {
        showError('Error loading data: ' + error.message);
    }
}

// Process topology data to create connection map
function processConnections() {
    nodeConnections.clear();

    // Initialize all nodes with empty connection arrays
    allNodes.forEach(node => {
        nodeConnections.set(node.node_id, {
            node: node,
            connections: []
        });
    });

    // Process topology links
    allTopology.forEach(link => {
        // Add forward connection (source -> neighbor)
        if (nodeConnections.has(link.source_node_id)) {
            nodeConnections.get(link.source_node_id).connections.push({
                node_id: link.neighbor_node_id,
                quality: link.link_quality_score,
                snr: link.avg_snr,
                rssi: link.avg_rssi,
                packets: link.total_packets,
                lastHeard: link.last_heard_utc
            });
        }

        // Add reverse connection (neighbor -> source) if not already present
        if (nodeConnections.has(link.neighbor_node_id)) {
            const neighborConnections = nodeConnections.get(link.neighbor_node_id).connections;
            if (!neighborConnections.find(c => c.node_id === link.source_node_id)) {
                neighborConnections.push({
                    node_id: link.source_node_id,
                    quality: link.link_quality_score,
                    snr: link.avg_snr,
                    rssi: link.avg_rssi,
                    packets: link.total_packets,
                    lastHeard: link.last_heard_utc
                });
            }
        }
    });
}

// Display all node connections
function displayConnections() {
    const container = document.getElementById('connections-container');
    const filterValue = document.getElementById('filter-connections').value;
    const searchTerm = document.getElementById('search').value.toLowerCase();

    let nodesToDisplay = Array.from(nodeConnections.values());

    // Apply filters
    if (filterValue === 'connected') {
        nodesToDisplay = nodesToDisplay.filter(nc => nc.connections.length > 0);
    } else if (filterValue === 'isolated') {
        nodesToDisplay = nodesToDisplay.filter(nc => nc.connections.length === 0);
    }

    // Apply search
    if (searchTerm) {
        nodesToDisplay = nodesToDisplay.filter(nc => {
            const name = (nc.node.long_name || nc.node.short_name || '').toLowerCase();
            const id = nc.node.node_id.toLowerCase();
            return name.includes(searchTerm) || id.includes(searchTerm);
        });
    }

    // Sort by number of connections (descending)
    nodesToDisplay.sort((a, b) => b.connections.length - a.connections.length);

    if (nodesToDisplay.length === 0) {
        container.innerHTML = '<p class="no-data">No nodes found matching your criteria</p>';
        return;
    }

    container.innerHTML = nodesToDisplay.map(nc => {
        const node = nc.node;
        const nodeName = node.long_name || node.short_name || node.node_id;

        // Get connection details with node names
        const connections = nc.connections.map(conn => {
            const connNode = allNodes.find(n => n.node_id === conn.node_id);
            const connName = connNode ? (connNode.long_name || connNode.short_name || conn.node_id) : conn.node_id;

            const qualityClass = conn.quality >= 80 ? 'quality-high' : conn.quality >= 50 ? 'quality-medium' : 'quality-low';

            return `
                <div class="connection-item ${qualityClass}">
                    <div class="connection-node">
                        <strong>${connName}</strong>
                        <br><small>${conn.node_id}</small>
                    </div>
                    <div class="connection-stats">
                        <span class="badge">Quality: ${Math.round(conn.quality)}%</span>
                        ${conn.snr ? `<span class="badge">SNR: ${conn.snr.toFixed(1)} dB</span>` : ''}
                        ${conn.rssi ? `<span class="badge">RSSI: ${conn.rssi} dBm</span>` : ''}
                        <span class="badge">Packets: ${conn.packets}</span>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="node-connections-card">
                <div class="node-header">
                    <h3>${nodeName}</h3>
                    <div class="node-info">
                        <span class="badge">${node.node_id}</span>
                        <span class="badge connection-count">${nc.connections.length} connection${nc.connections.length !== 1 ? 's' : ''}</span>
                    </div>
                </div>
                <div class="connections-list">
                    ${connections || '<p class="text-muted">No active connections</p>'}
                </div>
            </div>
        `;
    }).join('');
}

// Update statistics
function updateStats() {
    document.getElementById('stat-total-nodes').textContent = allNodes.length;
    document.getElementById('stat-active-links').textContent = allTopology.length;

    // Calculate average connections per node
    const totalConnections = Array.from(nodeConnections.values())
        .reduce((sum, nc) => sum + nc.connections.length, 0);
    const avgConnections = allNodes.length > 0 ? (totalConnections / allNodes.length).toFixed(1) : 0;
    document.getElementById('stat-avg-connections').textContent = avgConnections;
}

// Show error message
function showError(message) {
    const container = document.getElementById('connections-container');
    container.innerHTML = `<p class="error">${message}</p>`;
}

// Event listeners
document.getElementById('refresh-btn').addEventListener('click', loadData);
document.getElementById('search').addEventListener('input', displayConnections);
document.getElementById('filter-connections').addEventListener('change', displayConnections);

// Initial load
loadData();

// Auto-refresh every 30 seconds
setInterval(loadData, 30000);
