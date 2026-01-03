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
                'ROUTING_APP',
                'TRACEROUTE_APP'
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

            # Process traceroute packets for detailed topology
            if portnum == 'TRACEROUTE_APP':
                self._process_traceroute(packet, interface)

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
    
    def _match_relay_node(self, partial_id: int, interface, source_node_id: str) -> Optional[Dict[str, str]]:
        """
        Match a partial relay node ID (last byte) to an actual node.

        Args:
            partial_id: The partial node ID from relayNode field (last byte)
            interface: Meshtastic interface with node database
            source_node_id: The source node ID (to exclude from matches)

        Returns:
            Dict with 'id' and 'name' of matched node, or None if no match
        """
        try:
            # Get all known nodes from interface
            if not hasattr(interface, 'nodes') or not interface.nodes:
                return None

            matches = []

            # Check each known node
            for node_num, node_info in interface.nodes.items():
                # Skip the source node (packet didn't relay through itself)
                node_id = node_info.get('user', {}).get('id')
                if node_id == source_node_id:
                    continue

                # Extract last byte of this node's number
                # relayNode contains the last 8 bits of the node number
                last_byte = node_num & 0xFF

                if last_byte == (partial_id & 0xFF):
                    # Found a match!
                    user = node_info.get('user', {})
                    node_name = user.get('longName') or user.get('shortName') or node_id or f"!{node_num:08x}"

                    # Get additional info for heuristics
                    snr = node_info.get('snr', -999)
                    last_heard = node_info.get('lastHeard', 0)

                    matches.append({
                        'id': node_id or f"!{node_num:08x}",
                        'name': node_name,
                        'num': node_num,
                        'snr': snr,
                        'last_heard': last_heard
                    })

            if not matches:
                return None

            if len(matches) == 1:
                # Single match - use it
                return matches[0]

            # Multiple matches - use heuristics to pick best one
            # Prefer nodes with:
            # 1. Recent activity (last_heard)
            # 2. Better signal quality (SNR)
            # 3. More likely to be a relay (topology data could be added here)

            # Sort by last_heard (most recent first), then by SNR (best first)
            matches.sort(key=lambda x: (x['last_heard'], x['snr']), reverse=True)

            best_match = matches[0]

            # Log when there are multiple matches
            if len(matches) > 1:
                others = ', '.join([m['name'] for m in matches[1:]])
                logger.info(f"Multiple relay matches for {partial_id:#x}: chose {best_match['name']}, also matched: {others}")

            return best_match

        except Exception as e:
            logger.warn(f"Error matching relay node: {e}")
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

            # Extract relay node (if available in packet)
            # As of Meshtastic firmware 2.x, relayNode field is available
            # NOTE: relayNode contains only the LAST BITS of the node ID (not full ID)
            # We need to match it against known nodes to find the actual relay
            relay_node_partial = packet.get('relayNode')
            if relay_node_partial is not None and packet_data.get('hops_away', 0) > 0:
                matched_relay = self._match_relay_node(relay_node_partial, interface, node_id)
                if matched_relay:
                    # Validate that we got a full node ID (starts with !)
                    matched_id = matched_relay['id']
                    if isinstance(matched_id, str) and matched_id.startswith('!'):
                        packet_data['relay_node_id'] = matched_id
                        packet_data['relay_node_name'] = matched_relay['name']
                        logger.info(f"Packet from {node_id} relayed via {matched_relay['name']} (matched {relay_node_partial:#x})")
                    else:
                        logger.warn(f"Matched relay node has invalid ID format: {matched_id} for packet from {node_id}")
                else:
                    logger.warn(f"Could not match relay node {relay_node_partial:#x} for packet from {node_id}")
            
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

            # Extract traceroute data if TRACEROUTE_APP
            if decoded.get('portnum') == 'TRACEROUTE_APP':
                traceroute = decoded.get('traceroute', {})
                route = traceroute.get('route', [])
                if route:
                    # Store the route as JSON
                    import json
                    packet_data['message_text'] = f"Traceroute: {len(route)} hops"
                    # Store full route in raw_packet field (already serialized)

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

    def _process_traceroute(self, packet: Dict[str, Any], interface):
        """Process traceroute packets to build detailed topology"""
        try:
            decoded = packet.get('decoded', {})
            traceroute = decoded.get('traceroute', {})

            # Get the route from the traceroute packet
            route = traceroute.get('route', [])

            if not route or len(route) < 2:
                logger.info("Traceroute packet has no usable route data")
                return

            logger.infogreen(f"Processing traceroute with {len(route)} hops")

            # Convert node numbers to node IDs
            route_ids = []
            for node_num in route:
                # Try to find the node ID from the interface's node database
                node_info = None
                if hasattr(interface, 'nodes') and interface.nodes:
                    node_info = interface.nodes.get(node_num)

                if node_info:
                    node_id = node_info.get('user', {}).get('id')
                    if node_id:
                        route_ids.append(node_id)
                    else:
                        # Fallback: construct ID from node number
                        route_ids.append(f"!{node_num:08x}")
                else:
                    # Node not in database yet, construct ID
                    route_ids.append(f"!{node_num:08x}")

            # Process each hop in the route
            for i in range(len(route_ids) - 1):
                source_id = route_ids[i]
                target_id = route_ids[i + 1]

                # Get SNR/RSSI if available (some traceroute implementations include this)
                snr = traceroute.get('snr', [None] * len(route))[i] if traceroute.get('snr') else None
                rssi = None  # Not typically in traceroute, but could be added

                # Update topology link for this hop
                NodeTracking._db.update_topology(
                    source_id,
                    target_id,
                    snr=snr,
                    rssi=rssi,
                    hop_count=1  # Each link in traceroute is 1 hop
                )

                logger.info(f"  Traceroute hop {i+1}: {source_id} -> {target_id}")

            logger.infogreen(f"Traceroute processed: {' -> '.join([rid[-4:] for rid in route_ids])}")

        except Exception as e:
            logger.warn(f"Error processing traceroute: {e}")
            import traceback
            traceback.print_exc()
    
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