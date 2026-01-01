"""
Node Data Export Utilities
Handles JSON export of node data for external consumption and web display.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import plugins.liblogger as logger

class NodeExporter:
    """Handles export of node tracking data to JSON format"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def export_nodes_to_json(self, filepath: str = "./nodes.json", 
                            include_packets: bool = False,
                            include_topology: bool = True) -> bool:
        """Export all node data to JSON file"""
        try:
            data = {
                'metadata': {
                    'export_time': datetime.utcnow().isoformat(),
                    'version': '1.0'
                },
                'statistics': self.db.get_statistics(),
                'nodes': []
            }
            
            # Get all nodes
            nodes = self.db.get_all_nodes()
            
            for node in nodes:
                node_data = {
                    'node_id': node['node_id'],
                    'node_num': node['node_num'],
                    'short_name': node['short_name'],
                    'long_name': node['long_name'],
                    'position': {
                        'latitude': node['latitude'],
                        'longitude': node['longitude'],
                        'altitude': node['altitude']
                    } if node['latitude'] and node['longitude'] else None,
                    'last_seen': node['last_seen_utc'],
                    'first_seen': node['first_seen_utc'],
                    'total_packets': node['total_packets_received'],
                    'hardware': {
                        'model': node['hardware_model'],
                        'firmware': node['firmware_version']
                    },
                    'battery': {
                        'level': node['battery_level'],
                        'voltage': node['voltage'],
                        'is_charging': bool(node['is_charging']) if node['is_charging'] is not None else None,
                        'is_powered': bool(node['is_powered']) if node['is_powered'] is not None else None,
                        'last_update': node['last_battery_update_utc']
                    } if node['battery_level'] is not None else None,
                    'is_mqtt': bool(node['is_mqtt'])
                }
                
                # Include packet history if requested
                if include_packets:
                    packets = self.db.get_node_packets(node['node_id'], limit=100)
                    node_data['recent_packets'] = [self._format_packet(p) for p in packets]
                
                # Include neighbor information
                if include_topology:
                    neighbors = self.db.get_neighbors(node['node_id'])
                    node_data['neighbors'] = [self._format_neighbor(n) for n in neighbors]
                
                data['nodes'].append(node_data)
            
            # Add topology data
            if include_topology:
                topology = self.db.get_topology(active_only=True)
                data['topology'] = {
                    'links': [self._format_topology_link(link) for link in topology]
                }
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(nodes)} nodes to {filepath}")
            return True
            
        except Exception as e:
            logger.warn(f"Failed to export nodes to JSON: {e}")
            return False
    
    def _format_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Format packet data for JSON export"""
        return {
            'received_at': packet['received_at_utc'],
            'type': packet['packet_type'],
            'channel': packet['channel_index'],
            'hops': {
                'start': packet['hop_start'],
                'limit': packet['hop_limit'],
                'away': packet['hops_away']
            } if packet['hop_start'] is not None else None,
            'via_mqtt': bool(packet['via_mqtt']),
            'relay': {
                'node_id': packet['relay_node_id'],
                'name': packet['relay_node_name']
            } if packet['relay_node_id'] else None,
            'signal': {
                'snr': packet['rx_snr'],
                'rssi': packet['rx_rssi']
            } if packet['rx_snr'] is not None or packet['rx_rssi'] is not None else None,
            'position': {
                'latitude': packet['latitude'],
                'longitude': packet['longitude'],
                'altitude': packet['altitude']
            } if packet['latitude'] and packet['longitude'] else None,
            'telemetry': {
                'battery_level': packet['battery_level'],
                'voltage': packet['voltage'],
                'is_charging': bool(packet['is_charging']) if packet['is_charging'] is not None else None,
                'temperature': packet['temperature'],
                'humidity': packet['humidity'],
                'pressure': packet['pressure']
            } if any([packet['battery_level'], packet['temperature'], packet['humidity'], packet['pressure']]) else None,
            'message': packet['message_text']
        }
    
    def _format_neighbor(self, neighbor: Dict[str, Any]) -> Dict[str, Any]:
        """Format neighbor data for JSON export"""
        return {
            'neighbor_id': neighbor['neighbor_node_id'] if neighbor['source_node_id'] != neighbor['neighbor_node_id'] else neighbor['source_node_id'],
            'last_heard': neighbor['last_heard_utc'],
            'packets': neighbor['total_packets'],
            'link_quality': neighbor['link_quality_score']
        }
    
    def _format_topology_link(self, link: Dict[str, Any]) -> Dict[str, Any]:
        """Format topology link for JSON export"""
        return {
            'source': link['source_node_id'],
            'target': link['neighbor_node_id'],
            'quality': link['link_quality_score'],
            'packets': link['total_packets'],
            'signal': {
                'avg_snr': link['avg_snr'],
                'avg_rssi': link['avg_rssi'],
                'min_snr': link['min_snr'],
                'max_snr': link['max_snr'],
                'min_rssi': link['min_rssi'],
                'max_rssi': link['max_rssi']
            },
            'last_heard': link['last_heard_utc'],
            'active': bool(link['is_active'])
        }
    
    def export_for_web(self, output_dir: str = "./web/data") -> bool:
        """Export data in format optimized for web display"""
        try:
            import os
            os.makedirs(output_dir, exist_ok=True)
            
            # Export nodes list
            nodes = self.db.get_all_nodes()
            nodes_data = []
            
            for node in nodes:
                nodes_data.append({
                    'id': node['node_id'],
                    'num': node['node_num'],
                    'short': node['short_name'],
                    'long': node['long_name'],
                    'lat': node['latitude'],
                    'lon': node['longitude'],
                    'alt': node['altitude'],
                    'lastSeen': node['last_seen_utc'],
                    'packets': node['total_packets_received'],
                    'battery': node['battery_level'],
                    'voltage': node['voltage'],
                    'charging': bool(node['is_charging']) if node['is_charging'] is not None else None,
                    'hardware': node['hardware_model'],
                    'mqtt': bool(node['is_mqtt'])
                })
            
            with open(f"{output_dir}/nodes.json", 'w') as f:
                json.dump(nodes_data, f)
            
            # Export topology
            topology = self.db.get_topology(active_only=True)
            topology_data = {
                'nodes': [{'id': n['node_id'], 'name': n['long_name'] or n['short_name'] or n['node_id']} 
                         for n in nodes],
                'links': []
            }
            
            for link in topology:
                topology_data['links'].append({
                    'source': link['source_node_id'],
                    'target': link['neighbor_node_id'],
                    'quality': link['link_quality_score'],
                    'snr': link['avg_snr'],
                    'rssi': link['avg_rssi'],
                    'packets': link['total_packets']
                })
            
            with open(f"{output_dir}/topology.json", 'w') as f:
                json.dump(topology_data, f)
            
            # Export statistics
            stats = self.db.get_statistics()
            with open(f"{output_dir}/stats.json", 'w') as f:
                json.dump(stats, f)
            
            logger.info(f"Exported data for web to {output_dir}")
            return True
            
        except Exception as e:
            logger.warn(f"Failed to export for web: {e}")
            return False
    
    def get_nodes_geojson(self) -> Dict[str, Any]:
        """Export nodes as GeoJSON for mapping"""
        try:
            nodes = self.db.get_all_nodes()
            
            features = []
            for node in nodes:
                if node['latitude'] and node['longitude']:
                    feature = {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [node['longitude'], node['latitude']]
                        },
                        'properties': {
                            'id': node['node_id'],
                            'name': node['long_name'] or node['short_name'],
                            'battery': node['battery_level'],
                            'lastSeen': node['last_seen_utc'],
                            'packets': node['total_packets_received']
                        }
                    }
                    features.append(feature)
            
            return {
                'type': 'FeatureCollection',
                'features': features
            }
            
        except Exception as e:
            logger.warn(f"Failed to create GeoJSON: {e}")
            return {'type': 'FeatureCollection', 'features': []}