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
let topologySimulation = null;
let topologyData = null;
let topologySvg = null;

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
            <td>${formatLastSeen(node.last_seen_utc)}</td>
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

// Format Time (relative)
function formatTime(isoString) {
    if (!isoString) return 'Never';

    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 1) return 'seconds ago';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString();
}

// Format timestamp for "Last Seen" - shows actual time and relative time
function formatLastSeen(isoString) {
    if (!isoString) return 'Never';

    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    // Format the actual timestamp
    const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });

    // Format relative time
    let relativeTime;
    if (minutes < 1) relativeTime = 'just now';
    else if (minutes < 60) relativeTime = `${minutes}m ago`;
    else if (hours < 24) relativeTime = `${hours}h ago`;
    else if (days < 7) relativeTime = `${days}d ago`;
    else relativeTime = `${days}d ago`;

    // Show both actual time and relative time
    return `<div style="white-space: nowrap;">${dateStr} ${timeStr}</div><div style="font-size: 0.85em; color: #6c757d;">${relativeTime}</div>`;
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
                ${(() => {
                    // Find most recent packet with relay info
                    if (packetsData.success && packetsData.packets.length > 0) {
                        const recentPacket = packetsData.packets[0];
                        if (recentPacket.relay_node_id && recentPacket.relay_node_name) {
                            return `
                                <div class="detail-item">
                                    <span class="detail-label">Relayed Via:</span>
                                    <span class="detail-value" style="font-weight: 600; color: #667eea;">
                                        ${escapeHtml(recentPacket.relay_node_name)}
                                        <span style="font-size: 0.85em; color: #6c757d; font-family: monospace;">
                                            (${escapeHtml(recentPacket.relay_node_id)})
                                        </span>
                                    </span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Hop Distance:</span>
                                    <span class="detail-value">${recentPacket.hops_away !== null ? recentPacket.hops_away + ' hop' + (recentPacket.hops_away !== 1 ? 's' : '') : 'Unknown'}</span>
                                </div>
                            `;
                        } else if (recentPacket.hops_away === 0) {
                            return `
                                <div class="detail-item">
                                    <span class="detail-label">Connection:</span>
                                    <span class="detail-value" style="font-weight: 600; color: #28a745;">Direct (0 hops)</span>
                                </div>
                            `;
                        } else if (recentPacket.hops_away > 0) {
                            return `
                                <div class="detail-item">
                                    <span class="detail-label">Connection:</span>
                                    <span class="detail-value">Relayed (${recentPacket.hops_away} hop${recentPacket.hops_away !== 1 ? 's' : ''})</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Relay Node:</span>
                                    <span class="detail-value" style="color: #6c757d;">Unknown - not yet identified</span>
                                </div>
                            `;
                        }
                    }
                    return '';
                })()}
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
                            <th>Relay Node</th>
                            <th>Hops</th>
                            <th>SNR</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${packetsData.packets.map(p => `
                            <tr>
                                <td>${formatTime(p.received_at_utc)}</td>
                                <td>${p.packet_type || 'Unknown'}</td>
                                <td>${
                                    p.relay_node_id ?
                                        (p.relay_node_name || p.relay_node_id) :
                                        (p.hops_away === 0 ? 'Direct' :
                                         p.hops_away > 0 ? `Relayed (${p.hops_away} hop${p.hops_away !== 1 ? 's' : ''})` :
                                         'Unknown')
                                }</td>
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
    const graphContainer = document.getElementById('topology-graph');
    const infoContainer = document.getElementById('topology-info');

    graphContainer.innerHTML = '<p class="loading">Loading topology...</p>';
    infoContainer.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/api/topology/hop-graph`);
        const data = await response.json();

        if (data.success) {
            topologyData = data;
            renderTopology();
        } else {
            throw new Error(data.error || 'Failed to load topology');
        }
    } catch (error) {
        console.error('Failed to load topology:', error);
        graphContainer.innerHTML = `<p style="color: #dc3545;">Error loading topology: ${error.message}</p>`;
    }
}

// Render Topology with D3.js
function renderTopology() {
    const graphContainer = document.getElementById('topology-graph');
    const infoContainer = document.getElementById('topology-info');

    console.log('renderTopology called', {
        hasData: !!topologyData,
        nodeCount: topologyData?.nodes?.length,
        edgeCount: topologyData?.edges?.length
    });

    if (!topologyData || !topologyData.nodes || topologyData.nodes.length === 0) {
        graphContainer.innerHTML = '<p class="info-message">No topology data available</p>';
        return;
    }

    // Clear previous content
    graphContainer.innerHTML = '';

    // Set up dimensions - ensure we have a valid width
    const containerWidth = graphContainer.clientWidth || graphContainer.offsetWidth || 800;
    const width = containerWidth > 0 ? containerWidth : 800;
    const height = 600;

    console.log('Container dimensions:', { width, height });

    // Helper function to get node color based on hop count
    function getNodeColor(hops) {
        if (hops === -1) return '#667eea';  // Purple - local node (self)
        if (hops === 0) return '#28a745';   // Green - direct
        if (hops === 1) return '#ffc107';   // Yellow - 1 hop
        if (hops < 99) return '#dc3545';    // Red - 2+ hops
        return '#6c757d';                    // Gray - unknown
    }

    try {
        // Create SVG
        const svg = d3.select('#topology-graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .style('background', 'linear-gradient(to bottom, #f8f9fa 0%, #ffffff 100%)')
            .call(d3.zoom()
                .scaleExtent([0.1, 4])
                .on('zoom', (event) => {
                    container.attr('transform', event.transform);
                }));

        console.log('SVG created:', svg.node());
        topologySvg = svg;

        // Create container for zoom/pan
        const container = svg.append('g');

        // Prepare data - create node lookup map
        const nodeMap = new Map();
        topologyData.nodes.forEach(node => {
            nodeMap.set(node.id, {
                id: node.id,
                label: node.label,
                hops: node.hops,
                battery: node.battery
            });
        });

        console.log('Processing nodes:', nodeMap.size);

        // Create links with source/target objects - filter to only include valid nodes
        const links = topologyData.edges
            .filter(edge => {
                const hasSource = nodeMap.has(edge.from);
                const hasTarget = nodeMap.has(edge.to);
                if (!hasSource || !hasTarget) {
                    console.warn(`Skipping edge ${edge.from} -> ${edge.to}: source=${hasSource}, target=${hasTarget}`);
                }
                return hasSource && hasTarget;
            })
            .map(edge => ({
                source: edge.from,
                target: edge.to,
                hops: edge.hops
            }));

        const nodes = Array.from(nodeMap.values());
        console.log('Nodes for simulation:', nodes.length, 'Links:', links.length, 'Filtered out:', topologyData.edges.length - links.length);

        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id(d => d.id)
                .distance(150))
            .force('charge', d3.forceManyBody()
                .strength(-400))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => d.hops === -1 ? 60 : 50));

        topologySimulation = simulation;

        // Create arrow markers for links
        svg.append('defs').selectAll('marker')
            .data(['arrow'])
            .enter()
            .append('marker')
            .attr('id', 'arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 30)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#667eea');

        // Create links
        const link = container.append('g')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', '#667eea')
            .attr('stroke-width', 2)
            .attr('marker-end', 'url(#arrow)')
            .attr('stroke-opacity', 0.6);

        console.log('Links created:', link.size());

        // Drag functions (defined before use)
        function dragStarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragEnded(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Create node groups
        const node = container.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .call(d3.drag()
                .on('start', dragStarted)
                .on('drag', dragged)
                .on('end', dragEnded))
            .on('click', (event, d) => {
                event.stopPropagation();
                showNodeDetails(d.id);
            })
            .style('cursor', 'pointer');

        console.log('Nodes created:', node.size());

        // Add circles to nodes (local node is larger)
        node.append('circle')
            .attr('r', d => d.hops === -1 ? 35 : 25)
            .attr('fill', d => getNodeColor(d.hops))
            .attr('stroke', d => d.hops === -1 ? '#764ba2' : '#667eea')
            .attr('stroke-width', d => d.hops === -1 ? 4 : 3);

        // Add labels to nodes
        node.append('text')
            .text(d => d.label.length > 15 ? d.label.substring(0, 12) + '...' : d.label)
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .attr('fill', '#ffffff')
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .attr('pointer-events', 'none');

        // Add tooltips
        node.append('title')
            .text(d => `${d.label}\nHops: ${d.hops === 99 ? 'Unknown' : d.hops}\nBattery: ${d.battery || 'N/A'}%`);

        // Update positions on each tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node
                .attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Show info summary (exclude local node from counts)
        const directNodes = topologyData.nodes.filter(n => n.hops === 0).length;
        const oneHopNodes = topologyData.nodes.filter(n => n.hops === 1).length;
        const multiHopNodes = topologyData.nodes.filter(n => n.hops > 1 && n.hops < 99).length;
        const totalNodes = directNodes + oneHopNodes + multiHopNodes;

        infoContainer.innerHTML = `
            <div style="padding: 15px; background: #f8f9fa; border-radius: 8px; margin-top: 15px;">
                <h4 style="margin-top: 0; color: #667eea;">Network Summary</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div style="padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #667eea;">
                        <strong>Local Device:</strong> Self
                    </div>
                    <div style="padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #28a745;">
                        <strong>Direct (0 hops):</strong> ${directNodes}
                    </div>
                    <div style="padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #ffc107;">
                        <strong>1 Hop Away:</strong> ${oneHopNodes}
                    </div>
                    <div style="padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #dc3545;">
                        <strong>2+ Hops Away:</strong> ${multiHopNodes}
                    </div>
                    <div style="padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #667eea;">
                        <strong>Total Nodes:</strong> ${totalNodes}
                    </div>
                </div>
            </div>
        `;

        console.log('Topology graph rendered successfully');

    } catch (error) {
        console.error('Error rendering topology:', error);
        graphContainer.innerHTML = `<p class="info-message" style="color: #dc3545;">Error rendering graph: ${error.message}</p>`;
    }
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