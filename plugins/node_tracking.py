"""
Node Tracking Plugin
Captures and stores information about all nodes and packets received on the mesh network.
"""

import plugins
import cfg
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import plugins.liblogger as logger
import plugins.libmesh as LibMesh
from plugins.libnode_db import NodeDatabase
from plugins.libnode_export import NodeExporter
import threading
import time

class NodeTracking(plugins.Base):
    """Main plugin for node tracking and network topology"""
    
    # Class variables shared across all instances
    _db = None
    _exporter = None
    _config = None
    _last_export_time = 0
    _export_interval = 60  # Export every 60 seconds
    _topology_cleanup_timer = None
    
    def __init__(self):
        pass
    
    def start(self):
        """Initialize the node tracking system"""
        logger.info("Loading node tracking plugin")
        
        # Load configuration
        NodeTracking._config = cfg.config.get('node_tracking', {
            'enabled': True,
            'max_packets_per_node': 1000,
            'database_path': './nodes.db',
            'json_export_path': './nodes.json',
            'auto_export_json': True,
            'web_server': {
                'enabled': False,  # Will be implemented later
                'host': '0.0.0.0',
                'port': 8080
            },
            'track_packet_types': [
                'TEXT_MESSAGE_APP',
                'POSITION_APP',
                'NODEINFO_APP',
                'TELEMETRY_APP',
                'ROUTING_APP'
            ],
            'topology': {
                'enabled': True,
                'link_timeout_minutes': 60,
                'min_packets_for_link': 3,
                'calculate_link_quality': True
            }
        })
        
        if not NodeTracking._config.get('enabled', True):
            logger.info("Node tracking is disabled in config")
            return
        
        # Initialize database
        try:
            db_path = NodeTracking._config.get('database_path', './nodes.db')
            NodeTracking._db = NodeDatabase(db_path)
            NodeTracking._exporter = NodeExporter(NodeTracking._db)
            logger.infogreen(f"Node tracking database initialized at {db_path}")
        except Exception as e:
            logger.warn(f"Failed to initialize node tracking: {e}")
            NodeTracking._config['enabled'] = False
            return
        
        # Start topology cleanup timer if enabled
        if NodeTracking._config.get('topology', {}).get('enabled', True):
            self._start_topology_cleanup()
    
    def onReceive(self, packet, interface, client):
        """Handle incoming packets"""
        if not NodeTracking._config or not NodeTracking._config.get('enabled', True) or not NodeTracking._db:
            return
        
        try:
            # Extract basic packet info
            node_id = packet.get('fromId')
            if not node_id:
                return
            
            # Extract node information
            node_data = self._extract_node_data(packet, interface)
            
            # Update node in database
            if node_data:
                NodeTracking._db.upsert_node(node_data)
            
            # Check if we should track this packet type
            portnum = packet.get('decoded', {}).get('portnum', '')
            track_types = NodeTracking._config.get('track_packet_types', [])
            
            if portnum in track_types or not track_types:
                # Extract and store packet data
                packet_data = self._extract_packet_data(packet, interface)
                if packet_data:
                    max_packets = NodeTracking._config.get('max_packets_per_node', 1000)
                    NodeTracking._db.insert_packet(packet_data, max_packets)
            
            # Update topology if enabled
            if NodeTracking._config.get('topology', {}).get('enabled', True):
                self._update_topology(packet, interface)
            
            # Auto-export if enabled
            if NodeTracking._config.get('auto_export_json', False):
                current_time = time.time()
                if current_time - NodeTracking._last_export_time > NodeTracking._export_interval:
                    self._export_data()
                    NodeTracking._last_export_time = current_time
                    
        except Exception as e:
            logger.warn(f"Error in node tracking onReceive: {e}")
    
    def _extract_node_data(self, packet: Dict[str, Any], interface) -> Optional[Dict[str, Any]]:
        """Extract node information from packet"""
        try:
            node_id = packet.get('fromId')
            if not node_id:
                return None
            
            node_data = {
                'node_id': node_id,
                'node_num': packet.get('from'),
                'is_mqtt': packet.get('viaMqtt', False)
            }
            
            # Get node info from interface
            node = LibMesh.getNode(interface, packet)
            if node:
                if 'user' in node:
                    node_data['short_name'] = node['user'].get('shortName')
                    node_data['long_name'] = node['user'].get('longName')
                    node_data['hardware_model'] = node['user'].get('hwModel')
                
                # Position data
                if 'position' in node:
                    pos = node['position']
                    node_data['latitude'] = pos.get('latitude')
                    node_data['longitude'] = pos.get('longitude')
                    node_data['altitude'] = pos.get('altitude')
                
                # Device metrics (battery, etc.)
                if 'deviceMetrics' in node:
                    metrics = node['deviceMetrics']
                    node_data['battery_level'] = metrics.get('batteryLevel')
                    node_data['voltage'] = metrics.get('voltage')
                    node_data['is_charging'] = metrics.get('airUtilTx') is not None  # Approximate
            
            # Extract from packet if NODEINFO_APP
            if packet.get('decoded', {}).get('portnum') == 'NODEINFO_APP':
                user_info = packet.get('decoded', {}).get('user', {})
                if user_info:
                    node_data['short_name'] = user_info.get('shortName')
                    node_data['long_name'] = user_info.get('longName')
                    node_data['hardware_model'] = user_info.get('hwModel')
            
            # Extract position from POSITION_APP packet
            if packet.get('decoded', {}).get('portnum') == 'POSITION_APP':
                position = packet.get('decoded', {}).get('position', {})
                if position:
                    node_data['latitude'] = position.get('latitude')
                    node_data['longitude'] = position.get('longitude')
                    node_data['altitude'] = position.get('altitude')
            
            # Extract telemetry from TELEMETRY_APP packet
            if packet.get('decoded', {}).get('portnum') == 'TELEMETRY_APP':
                telemetry = packet.get('decoded', {}).get('telemetry', {})
                if 'deviceMetrics' in telemetry:
                    metrics = telemetry['deviceMetrics']
                    node_data['battery_level'] = metrics.get('batteryLevel')
                    node_data['voltage'] = metrics.get('voltage')
            
            return node_data
            
        except Exception as e:
            logger.warn(f"Error extracting node data: {e}")
            return None
    
    def _extract_packet_data(self, packet: Dict[str, Any], interface) -> Optional[Dict[str, Any]]:
        """Extract packet data for storage"""
        try:
            node_id = packet.get('fromId')
            if not node_id:
                return None
            
            decoded = packet.get('decoded', {})
            
            packet_data = {
                'node_id': node_id,
                'received_at_utc': datetime.utcnow().isoformat(),
                'packet_type': decoded.get('portnum'),
                'channel_index': packet.get('channel', 0),
                'hop_start': packet.get('hopStart'),
                'hop_limit': packet.get('hopLimit'),
                'via_mqtt': packet.get('viaMqtt', False),
                'rx_snr': packet.get('rxSnr'),
                'rx_rssi': packet.get('rxRssi'),
                'raw_packet': self._serialize_packet(packet)
            }
            
            # Calculate hops away
            if packet_data['hop_start'] and packet_data['hop_limit']:
                packet_data['hops_away'] = packet_data['hop_start'] - packet_data['hop_limit']
            
            # Extract relay node (if forwarded)
            # Note: Meshtastic doesn't directly expose relay node in packet
            # We can infer it from hopLimit changes in topology tracking
            
            # Extract position if POSITION_APP
            if decoded.get('portnum') == 'POSITION_APP':
                position = decoded.get('position', {})
                packet_data['latitude'] = position.get('latitude')
                packet_data['longitude'] = position.get('longitude')
                packet_data['altitude'] = position.get('altitude')
            
            # Extract telemetry if TELEMETRY_APP
            if decoded.get('portnum') == 'TELEMETRY_APP':
                telemetry = decoded.get('telemetry', {})
                
                if 'deviceMetrics' in telemetry:
                    metrics = telemetry['deviceMetrics']
                    packet_data['battery_level'] = metrics.get('batteryLevel')
                    packet_data['voltage'] = metrics.get('voltage')
                    packet_data['temperature'] = metrics.get('temperature')
                
                if 'environmentMetrics' in telemetry:
                    env = telemetry['environmentMetrics']
                    packet_data['temperature'] = env.get('temperature')
                    packet_data['humidity'] = env.get('relativeHumidity')
                    packet_data['pressure'] = env.get('barometricPressure')
            
            # Extract text message if TEXT_MESSAGE_APP
            if decoded.get('portnum') == 'TEXT_MESSAGE_APP':
                packet_data['message_text'] = decoded.get('text')
            
            return packet_data
            
        except Exception as e:
            logger.warn(f"Error extracting packet data: {e}")
            return None
    
    def _serialize_packet(self, packet: Dict[str, Any]) -> str:
        """Serialize packet to JSON, handling bytes and protobuf objects"""
        try:
            def convert_to_serializable(obj):
                """Convert non-JSON-serializable objects for storage"""
                # Handle bytes
                if isinstance(obj, bytes):
                    return base64.b64encode(obj).decode('utf-8')
                
                # Handle dictionaries recursively
                elif isinstance(obj, dict):
                    return {k: convert_to_serializable(v) for k, v in obj.items()}
                
                # Handle lists recursively
                elif isinstance(obj, list):
                    return [convert_to_serializable(item) for item in obj]
                
                # Handle protobuf objects and other complex types
                elif hasattr(obj, '__class__') and obj.__class__.__module__ not in ['builtins', '__builtin__']:
                    # Try to convert to string representation
                    try:
                        return str(obj)
                    except:
                        return f"<{obj.__class__.__name__}>"
                
                # Return primitive types as-is
                return obj
            
            cleaned_packet = convert_to_serializable(packet)
            return json.dumps(cleaned_packet)
        except Exception as e:
            logger.warn(f"Error serializing packet: {e}")
            return "{}"
    
    def _update_topology(self, packet: Dict[str, Any], interface):
        """Update network topology based on packet"""
        try:
            source_id = packet.get('fromId')
            if not source_id:
                return
            
            # If packet has hop information, we can infer it came through network
            hop_start = packet.get('hopStart')
            hop_limit = packet.get('hopLimit')
            
            if hop_start and hop_limit:
                hops_away = hop_start - hop_limit
                
                # If hops_away > 0, packet was relayed
                # For now, we'll track source -> our node link
                # In future, we could try to infer intermediate hops
                
                my_node_id = interface.getMyNodeInfo().get('user', {}).get('id')
                if my_node_id and source_id != my_node_id:
                    # Update link from source to us
                    NodeTracking._db.update_topology(
                        source_id,
                        my_node_id,
                        snr=packet.get('rxSnr'),
                        rssi=packet.get('rxRssi'),
                        hop_count=hops_away
                    )
            
            # If via MQTT, track MQTT gateway as neighbor
            if packet.get('viaMqtt'):
                # Could track MQTT gateway here if we knew its node_id
                pass
                
        except Exception as e:
            logger.warn(f"Error updating topology: {e}")
    
    def _export_data(self):
        """Export data to JSON"""
        try:
            if NodeTracking._exporter:
                json_path = NodeTracking._config.get('json_export_path', './nodes.json')
                NodeTracking._exporter.export_nodes_to_json(json_path, include_topology=True)
        except Exception as e:
            logger.warn(f"Error exporting data: {e}")
    
    def _start_topology_cleanup(self):
        """Start periodic topology cleanup timer"""
        def cleanup():
            try:
                timeout_minutes = NodeTracking._config.get('topology', {}).get('link_timeout_minutes', 60)
                NodeTracking._db.mark_inactive_links(timeout_minutes)
            except Exception as e:
                logger.warn(f"Error in topology cleanup: {e}")
            
            # Schedule next cleanup
            if NodeTracking._config.get('enabled', True):
                NodeTracking._topology_cleanup_timer = threading.Timer(300, cleanup)  # Every 5 minutes
                NodeTracking._topology_cleanup_timer.daemon = True
                NodeTracking._topology_cleanup_timer.start()
        
        # Start initial cleanup
        cleanup()
    
    def onConnect(self, interface, client):
        """Handle connection to node"""
        if not NodeTracking._config or not NodeTracking._config.get('enabled', True):
            return
        
        logger.info("Node tracking ready - will capture all packets")
        
        # Do initial export
        self._export_data()
    
    def onDisconnect(self, interface, client):
        """Handle disconnection from node"""
        if not NodeTracking._config or not NodeTracking._config.get('enabled', True):
            return
        
        # Export data before shutdown
        self._export_data()
        
        # Cancel cleanup timer
        if NodeTracking._topology_cleanup_timer:
            NodeTracking._topology_cleanup_timer.cancel()