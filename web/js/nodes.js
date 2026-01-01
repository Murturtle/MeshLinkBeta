// MeshLink Node Tracking - JavaScript

// API Configuration
const API_BASE = window.location.origin;

// Global State
let allNodes = [];
let allTopology = [];
let currentFilter = {
    search: '',
    battery: '',
    sortBy: 'lastSeen'
};
let map = null;
let mapMarkers = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeControls();
    initializeModal();
    loadStatistics();
    loadNodes();
    
    // Auto-refresh every 30 seconds
    setInterval(() => {
        if (document.querySelector('.tab-content.active').id === 'nodes-tab') {
            loadNodes(true);
        }
    }, 30000);
});

// Tab Management
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // Update buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${targetTab}-tab`).classList.add('active');
            
            // Load data for the active tab
            if (targetTab === 'topology') {
                loadTopology();
            } else if (targetTab === 'map') {
                loadMap();
            }
        });
    });
}

// Initialize Controls
function initializeControls() {
    // Search
    document.getElementById('search').addEventListener('input', (e) => {
        currentFilter.search = e.target.value.toLowerCase();
        renderNodes();
    });
    
    // Battery filter
    document.getElementById('filter-battery').addEventListener('change', (e) => {
        currentFilter.battery = e.target.value;
        renderNodes();
    });
    
    // Sort
    document.getElementById('sort-by').addEventListener('change', (e) => {
        currentFilter.sortBy = e.target.value;
        renderNodes();
    });
    
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadNodes();
        loadStatistics();
    });
    
    // Topology controls
    document.getElementById('refresh-topology-btn')?.addEventListener('click', loadTopology);
    document.getElementById('quality-filter')?.addEventListener('input', (e) => {
        document.getElementById('quality-value').textContent = e.target.value;
        renderTopology();
    });
}

// Modal Management
function initializeModal() {
    const modal = document.getElementById('node-modal');
    const closeBtn = document.querySelector('.close');
    
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Load Statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.statistics;
            document.getElementById('stat-total-nodes').textContent = stats.total_nodes || 0;
            document.getElementById('stat-active-nodes').textContent = stats.active_nodes || 0;
            document.getElementById('stat-total-packets').textContent = stats.total_packets || 0;
            document.getElementById('stat-active-links').textContent = stats.active_links || 0;
            document.getElementById('stat-avg-quality').textContent = `${stats.avg_link_quality || 0}%`;
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load Nodes
async function loadNodes(silent = false) {
    if (!silent) {
        document.getElementById('nodes-tbody').innerHTML = '<tr><td colspan="8" class="loading">Loading nodes...</td></tr>';
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/nodes`);
        const data = await response.json();
        
        if (data.success) {
            allNodes = data.nodes;
            renderNodes();
        } else {
            throw new Error(data.error || 'Failed to load nodes');
        }
    } catch (error) {
        console.error('Failed to load nodes:', error);
        document.getElementById('nodes-tbody').innerHTML = 
            `<tr><td colspan="8" class="loading" style="color: #dc3545;">Error loading nodes: ${error.message}</td></tr>`;
    }
}

// Render Nodes Table
function renderNodes() {
    let filteredNodes = [...allNodes];
    
    // Apply search filter
    if (currentFilter.search) {
        filteredNodes = filteredNodes.filter(node => {
            const searchText = currentFilter.search;
            return (node.long_name && node.long_name.toLowerCase().includes(searchText)) ||
                   (node.short_name && node.short_name.toLowerCase().includes(searchText)) ||
                   (node.node_id && node.node_id.toLowerCase().includes(searchText));
        });
    }
    
    // Apply battery filter
    if (currentFilter.battery) {
        filteredNodes = filteredNodes.filter(node => {
            if (!node.battery_level) return false;
            switch(currentFilter.battery) {
                case 'high': return node.battery_level > 60;
                case 'medium': return node.battery_level >= 20 && node.battery_level <= 60;
                case 'low': return node.battery_level < 20;
                default: return true;
            }
        });
    }
    
    // Sort nodes
    filteredNodes.sort((a, b) => {
        switch(currentFilter.sortBy) {
            case 'name':
                return (a.long_name || a.short_name || '').localeCompare(b.long_name || b.short_name || '');
            case 'battery':
                return (b.battery_level || 0) - (a.battery_level || 0);
            case 'packets':
                return (b.total_packets_received || 0) - (a.total_packets_received || 0);
            case 'lastSeen':
            default:
                return new Date(b.last_seen_utc || 0) - new Date(a.last_seen_utc || 0);
        }
    });
    
    const tbody = document.getElementById('nodes-tbody');
    
    if (filteredNodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No nodes found</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredNodes.map(node => `
        <tr>
            <td>
                <div class="node-name">${escapeHtml(node.long_name || node.short_name || 'Unknown')}</div>
                <div class="node-id">${escapeHtml(node.node_id)}</div>
            </td>
            <td>${getStatusBadge(node)}</td>
            <td>${getBatteryDisplay(node)}</td>
            <td>${getLocationDisplay(node)}</td>
            <td>${formatTime(node.last_seen_utc)}</td>
            <td>${node.total_packets_received || 0}</td>
            <td>${escapeHtml(node.hardware_model || 'Unknown')}</td>
            <td>
                <button class="btn btn-primary" onclick="showNodeDetails('${node.node_id}')">Details</button>
            </td>
        </tr>
    `).join('');
}

// Get Status Badge
function getStatusBadge(node) {
    const lastSeen = new Date(node.last_seen_utc);
    const now = new Date();
    const minutesAgo = (now - lastSeen) / 1000 / 60;
    
    if (minutesAgo < 5) {
        return '<span class="status-badge status-online">● Online</span>';
    } else if (minutesAgo < 60) {
        return '<span class="status-badge status-recent">● Recent</span>';
    } else {
        return '<span class="status-badge status-offline">● Offline</span>';
    }
}

// Get Battery Display
function getBatteryDisplay(node) {
    if (!node.battery_level) {
        return '<span class="text-muted">N/A</span>';
    }
    
    let batteryClass = 'battery-high';
    if (node.battery_level < 20) batteryClass = 'battery-low';
    else if (node.battery_level < 60) batteryClass = 'battery-medium';
    
    const chargingIcon = node.is_charging ? '<span class="battery-charging">⚡</span>' : '';
    
    return `
        <div class="battery-container">
            <div class="battery-bar">
                <div class="battery-fill ${batteryClass}" style="width: ${node.battery_level}%"></div>
            </div>
            <span>${node.battery_level}%</span>
            ${chargingIcon}
        </div>
    `;
}

// Get Location Display
function getLocationDisplay(node) {
    if (node.latitude && node.longitude) {
        const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${node.latitude},${node.longitude}`;
        return `<a href="${mapsUrl}" target="_blank" style="color: #667eea;">📍 View Map</a>`;
    }
    return '<span class="text-muted">No GPS</span>';
}

// Format Time
function formatTime(isoString) {
    if (!isoString) return 'Never';
    
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return date.toLocaleDateString();
}

// Show Node Details
async function showNodeDetails(nodeId) {
    const modal = document.getElementById('node-modal');
    const modalBody = document.getElementById('modal-body');
    const modalTitle = document.getElementById('modal-title');
    
    modalBody.innerHTML = '<p class="loading">Loading node details...</p>';
    modal.style.display = 'block';
    
    try {
        // Load node info and packets
        const [nodeRes, packetsRes, neighborsRes] = await Promise.all([
            fetch(`${API_BASE}/api/nodes/${nodeId}`),
            fetch(`${API_BASE}/api/nodes/${nodeId}/packets?limit=10`),
            fetch(`${API_BASE}/api/nodes/${nodeId}/neighbors`)
        ]);
        
        const nodeData = await nodeRes.json();
        const packetsData = await packetsRes.json();
        const neighborsData = await neighborsRes.json();
        
        if (!nodeData.success) throw new Error('Failed to load node');
        
        const node = nodeData.node;
        modalTitle.textContent = node.long_name || node.short_name || node.node_id;
        
        modalBody.innerHTML = `
            <div class="detail-section">
                <h3>Node Information</h3>
                <div class="detail-item">
                    <span class="detail-label">Node ID:</span>
                    <span class="detail-value">${escapeHtml(node.node_id)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Short Name:</span>
                    <span class="detail-value">${escapeHtml(node.short_name || 'N/A')}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Long Name:</span>
                    <span class="detail-value">${escapeHtml(node.long_name || 'N/A')}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Hardware:</span>
                    <span class="detail-value">${escapeHtml(node.hardware_model || 'Unknown')}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Firmware:</span>
                    <span class="detail-value">${escapeHtml(node.firmware_version || 'Unknown')}</span>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>Status</h3>
                <div class="detail-item">
                    <span class="detail-label">First Seen:</span>
                    <span class="detail-value">${formatTime(node.first_seen_utc)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Last Seen:</span>
                    <span class="detail-value">${formatTime(node.last_seen_utc)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Total Packets:</span>
                    <span class="detail-value">${node.total_packets_received || 0}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Via MQTT:</span>
                    <span class="detail-value">${node.is_mqtt ? 'Yes' : 'No'}</span>
                </div>
            </div>
            
            ${node.battery_level ? `
            <div class="detail-section">
                <h3>Battery & Power</h3>
                <div class="detail-item">
                    <span class="detail-label">Battery Level:</span>
                    <span class="detail-value">${node.battery_level}%</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Voltage:</span>
                    <span class="detail-value">${node.voltage ? node.voltage.toFixed(2) + 'V' : 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Charging:</span>
                    <span class="detail-value">${node.is_charging ? 'Yes ⚡' : 'No'}</span>
                </div>
            </div>
            ` : ''}
            
            ${node.latitude && node.longitude ? `
            <div class="detail-section">
                <h3>Location</h3>
                <div class="detail-item">
                    <span class="detail-label">Coordinates:</span>
                    <span class="detail-value">${node.latitude.toFixed(6)}, ${node.longitude.toFixed(6)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Altitude:</span>
                    <span class="detail-value">${node.altitude ? node.altitude.toFixed(0) + 'm' : 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Map:</span>
                    <span class="detail-value">
                        <a href="https://www.google.com/maps/search/?api=1&query=${node.latitude},${node.longitude}" target="_blank">
                            View on Google Maps
                        </a>
                    </span>
                </div>
            </div>
            ` : ''}
            
            ${neighborsData.success && neighborsData.neighbors.length > 0 ? `
            <div class="detail-section">
                <h3>Neighbors (${neighborsData.neighbors.length})</h3>
                ${neighborsData.neighbors.map(n => `
                    <div class="detail-item">
                        <span class="detail-label">${n.neighbor_node_id || n.source_node_id}:</span>
                        <span class="detail-value">Quality ${n.link_quality_score?.toFixed(0) || 0}%, ${n.total_packets || 0} packets</span>
                    </div>
                `).join('')}
            </div>
            ` : ''}
            
            ${packetsData.success && packetsData.packets.length > 0 ? `
            <div class="detail-section">
                <h3>Recent Packets (${packetsData.count})</h3>
                <table style="width: 100%; font-size: 0.9em;">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Type</th>
                            <th>Hops</th>
                            <th>SNR</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${packetsData.packets.map(p => `
                            <tr>
                                <td>${formatTime(p.received_at_utc)}</td>
                                <td>${p.packet_type || 'Unknown'}</td>
                                <td>${p.hops_away !== null ? p.hops_away : 'N/A'}</td>
                                <td>${p.rx_snr !== null ? p.rx_snr.toFixed(1) + ' dB' : 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            ` : ''}
        `;
        
    } catch (error) {
        console.error('Failed to load node details:', error);
        modalBody.innerHTML = `<p style="color: #dc3545;">Error loading node details: ${error.message}</p>`;
    }
}

// Load Topology
async function loadTopology() {
    const container = document.getElementById('topology-info');
    container.innerHTML = '<p class="loading">Loading topology...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/api/topology`);
        const data = await response.json();
        
        if (data.success) {
            allTopology = data.links;
            renderTopology();
        } else {
            throw new Error(data.error || 'Failed to load topology');
        }
    } catch (error) {
        console.error('Failed to load topology:', error);
        container.innerHTML = `<p style="color: #dc3545;">Error loading topology: ${error.message}</p>`;
    }
}

// Render Topology
function renderTopology() {
    const container = document.getElementById('topology-info');
    const qualityThreshold = parseInt(document.getElementById('quality-filter')?.value || 0);
    
    let filtered = allTopology.filter(link => 
        link.link_quality_score >= qualityThreshold
    );
    
    if (filtered.length === 0) {
        container.innerHTML = '<p class="info-message">No topology links found</p>';
        return;
    }
    
    container.innerHTML = filtered.map(link => {
        const qualityClass = link.link_quality_score > 70 ? 'link-quality-high' :
                           link.link_quality_score > 40 ? 'link-quality-medium' : 'link-quality-low';
        
        return `
            <div class="link-item ${qualityClass}">
                <strong>${link.source_node_id}</strong> ↔ <strong>${link.neighbor_node_id}</strong>
                <br>
                Quality: ${link.link_quality_score.toFixed(0)}% | 
                SNR: ${link.avg_snr?.toFixed(1) || 'N/A'} dB | 
                RSSI: ${link.avg_rssi || 'N/A'} dBm | 
                Packets: ${link.total_packets}
                <br>
                <small>Last heard: ${formatTime(link.last_heard_utc)}</small>
            </div>
        `;
    }).join('');
}

// Initialize Map
function initializeMap() {
    if (!map) {
        // Create map centered at a default location
        map = L.map('map').setView([0, 0], 2);

        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(map);
    }
}

// Load Map
function loadMap() {
    // Initialize the map if not already done
    initializeMap();

    // Clear existing markers
    mapMarkers.forEach(marker => marker.remove());
    mapMarkers = [];

    // Filter nodes with GPS coordinates
    const nodesWithGPS = allNodes.filter(n => n.latitude && n.longitude);

    if (nodesWithGPS.length === 0) {
        // Center map at default location if no nodes
        map.setView([0, 0], 2);
        return;
    }

    // Create markers for each node
    nodesWithGPS.forEach(node => {
        const marker = L.marker([node.latitude, node.longitude]).addTo(map);

        // Create popup content
        const popupContent = `
            <div style="min-width: 200px;">
                <strong>${escapeHtml(node.long_name || node.short_name || node.node_id)}</strong><br>
                <small style="color: #6c757d; font-family: monospace;">${escapeHtml(node.node_id)}</small><br><br>
                ${getStatusBadge(node)}<br><br>
                ${node.battery_level ? `🔋 Battery: ${node.battery_level}%<br>` : ''}
                📍 ${node.latitude.toFixed(6)}, ${node.longitude.toFixed(6)}<br>
                ${node.altitude ? `⛰️ Altitude: ${node.altitude.toFixed(0)}m<br>` : ''}
                📦 Packets: ${node.total_packets_received || 0}<br>
                🕐 ${formatTime(node.last_seen_utc)}<br><br>
                <button onclick="showNodeDetails('${node.node_id}')" style="padding: 4px 8px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    View Details
                </button>
            </div>
        `;

        marker.bindPopup(popupContent);
        mapMarkers.push(marker);
    });

    // Calculate bounds to fit all markers
    if (nodesWithGPS.length === 1) {
        // Single node - center on it with a reasonable zoom
        const node = nodesWithGPS[0];
        map.setView([node.latitude, node.longitude], 13);
    } else {
        // Multiple nodes - fit bounds to show all
        const bounds = L.latLngBounds(nodesWithGPS.map(n => [n.latitude, n.longitude]));
        map.fitBounds(bounds, { padding: [50, 50] });
    }

    // Force map to refresh its size (fixes rendering issues)
    setTimeout(() => {
        map.invalidateSize();
    }, 100);
}

// Utility: Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}