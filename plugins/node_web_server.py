"""
Node Tracking Web Server
Provides REST API and web interface for viewing node tracking data.
"""

import plugins
import cfg
import json
import os
from datetime import datetime
import plugins.liblogger as logger
from plugins.libnode_db import NodeDatabase
from plugins.libnode_export import NodeExporter
import threading

class NodeWebServer(plugins.Base):
    """Web server for node tracking visualization"""
    
    def __init__(self):
        self.server_thread = None
        self.app = None
        self.db = None
        self.exporter = None
        self.config = None
    
    def start(self):
        """Initialize and start the web server"""
        logger.info("Loading node tracking web server")
        
        # Get config
        node_config = cfg.config.get('node_tracking', {})
        if not node_config.get('enabled', False):
            logger.info("Node tracking disabled, skipping web server")
            return
        
        web_config = node_config.get('web_server', {})
        if not web_config.get('enabled', False):
            logger.info("Node tracking web server disabled")
            return
        
        self.config = web_config
        
        # Try to import Flask
        try:
            from flask import Flask, jsonify, send_from_directory, request
            from flask_cors import CORS
        except ImportError:
            logger.warn("Flask not installed. Install with: pip install flask flask-cors")
            logger.info("Web server disabled - Flask required")
            return
        
        # Initialize database connection
        try:
            db_path = node_config.get('database_path', './nodes.db')
            self.db = NodeDatabase(db_path)
            self.exporter = NodeExporter(self.db)
        except Exception as e:
            logger.warn(f"Failed to connect to node database: {e}")
            return
        
        # Get absolute path to web directory
        # Working directory is MeshLinkBeta/, so web/ is directly accessible
        web_dir = os.path.join(os.getcwd(), 'web')
        
        # Create Flask app
        self.app = Flask(__name__, static_folder=web_dir, static_url_path='')
        CORS(self.app)  # Enable CORS for API access
        
        # Define routes
        @self.app.route('/')
        def index():
            """Serve main page"""
            try:
                return send_from_directory(web_dir, 'nodes.html')
            except Exception as e:
                logger.warn(f"Failed to serve nodes.html: {e}")
                return "<h1>Node Tracking</h1><p>Web interface not yet available. Use API endpoints.</p>"
        
        @self.app.route('/api/nodes', methods=['GET'])
        def get_nodes():
            """Get all nodes"""
            try:
                nodes = self.db.get_all_nodes()
                return jsonify({
                    'success': True,
                    'count': len(nodes),
                    'nodes': nodes
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/nodes/<node_id>', methods=['GET'])
        def get_node(node_id):
            """Get specific node"""
            try:
                node = self.db.get_node(node_id)
                if node:
                    return jsonify({
                        'success': True,
                        'node': node
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Node not found'
                    }), 404
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/nodes/<node_id>/packets', methods=['GET'])
        def get_node_packets(node_id):
            """Get packet history for node"""
            try:
                limit = int(request.args.get('limit', 100))
                packets = self.db.get_node_packets(node_id, limit)
                return jsonify({
                    'success': True,
                    'count': len(packets),
                    'packets': packets
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/nodes/<node_id>/neighbors', methods=['GET'])
        def get_node_neighbors(node_id):
            """Get neighbors for node"""
            try:
                neighbors = self.db.get_neighbors(node_id)
                return jsonify({
                    'success': True,
                    'count': len(neighbors),
                    'neighbors': neighbors
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/topology', methods=['GET'])
        def get_topology():
            """Get network topology"""
            try:
                active_only = request.args.get('active_only', 'true').lower() == 'true'
                topology = self.db.get_topology(active_only)
                return jsonify({
                    'success': True,
                    'count': len(topology),
                    'links': topology
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/topology/graph', methods=['GET'])
        def get_topology_graph():
            """Get topology in graph format"""
            try:
                nodes = self.db.get_all_nodes()
                topology = self.db.get_topology(active_only=True)
                
                # Format for graph visualization
                graph = {
                    'nodes': [
                        {
                            'id': node['node_id'],
                            'label': node['long_name'] or node['short_name'] or node['node_id'],
                            'battery': node['battery_level'],
                            'lastSeen': node['last_seen_utc']
                        }
                        for node in nodes
                    ],
                    'edges': [
                        {
                            'source': link['source_node_id'],
                            'target': link['neighbor_node_id'],
                            'quality': link['link_quality_score'],
                            'snr': link['avg_snr'],
                            'rssi': link['avg_rssi']
                        }
                        for link in topology
                    ]
                }
                
                return jsonify({
                    'success': True,
                    'graph': graph
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/topology/hop-graph', methods=['GET'])
        def get_hop_topology():
            """Get topology organized by hop distance from local node"""
            try:
                # Get all nodes and their recent packets
                nodes = self.db.get_all_nodes()

                # Build hop-based graph
                graph_nodes = []
                graph_edges = []
                direct_nodes = []

                # Add a virtual "Self" node representing the local device
                graph_nodes.append({
                    'id': 'LOCAL_NODE',
                    'label': 'Self (This Device)',
                    'short_name': 'Self',
                    'long_name': 'Self (This Device)',
                    'hops': -1,  # Special marker for local node
                    'battery': None,
                    'lastSeen': None,
                    'relay_via': None
                })

                # Process each node
                for node in nodes:
                    node_id = node['node_id']

                    # Get recent packets from this node to determine hop count
                    packets = self.db.get_node_packets(node_id, limit=20)

                    # Determine minimum hop count and relay node
                    min_hops = None
                    relay_via = None

                    for pkt in packets:
                        hops = pkt.get('hops_away')
                        if hops is not None:
                            # Track minimum hop count
                            if min_hops is None or hops < min_hops:
                                min_hops = hops

                            # Get relay_via from most recent packet with hops > 0
                            # (not from the minimum hop packet, since that might be direct)
                            if hops > 0 and relay_via is None:
                                relay_via = pkt.get('relay_node_id')

                    # Add node to graph
                    graph_nodes.append({
                        'id': node_id,
                        'label': node.get('long_name') or node.get('short_name') or node_id,
                        'short_name': node.get('short_name'),
                        'long_name': node.get('long_name'),
                        'hops': min_hops if min_hops is not None else 99,
                        'battery': node.get('battery_level'),
                        'lastSeen': node.get('last_seen_utc'),
                        'relay_via': relay_via
                    })

                    # Create edges based on hop count
                    if min_hops == 0:
                        # Direct connection to local node
                        direct_nodes.append(node_id)
                        graph_edges.append({
                            'from': 'LOCAL_NODE',
                            'to': node_id,
                            'hops': 0
                        })
                    elif relay_via and min_hops and min_hops > 0:
                        # Relayed through another node
                        # Only add edge if relay_via is a valid full node ID (starts with !)
                        if isinstance(relay_via, str) and relay_via.startswith('!'):
                            graph_edges.append({
                                'from': relay_via,
                                'to': node_id,
                                'hops': min_hops
                            })
                        else:
                            # Skip invalid relay IDs (partial IDs from relay matching)
                            pass

                return jsonify({
                    'success': True,
                    'nodes': graph_nodes,
                    'edges': graph_edges
                })
            except Exception as e:
                logger.warn(f"Error getting hop topology: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """Get network statistics"""
            try:
                stats = self.db.get_statistics()
                return jsonify({
                    'success': True,
                    'statistics': stats
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/export/json', methods=['GET'])
        def export_json():
            """Export full data as JSON"""
            try:
                # Create temporary export
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                    temp_path = f.name
                
                self.exporter.export_nodes_to_json(temp_path, include_packets=True, include_topology=True)
                
                with open(temp_path, 'r') as f:
                    data = json.load(f)
                
                os.unlink(temp_path)
                
                return jsonify(data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/export/geojson', methods=['GET'])
        def export_geojson():
            """Export nodes as GeoJSON"""
            try:
                geojson = self.exporter.get_nodes_geojson()
                return jsonify(geojson)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # Start server in background thread
        host = self.config.get('host', '0.0.0.0')
        port = self.config.get('port', 8080)
        
        def run_server():
            try:
                logger.infogreen(f"Node tracking web server starting on http://{host}:{port}")
                self.app.run(host=host, port=port, debug=False, use_reloader=False)
            except Exception as e:
                logger.warn(f"Web server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        logger.infogreen(f"Node tracking web interface available at http://{host}:{port}")