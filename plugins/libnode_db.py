"""
Node Database Manager
Handles all database operations for node tracking, packet history, and network topology.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
import threading
import plugins.liblogger as logger

# Thread-local storage for database connections
_thread_local = threading.local()

class NodeDatabase:
    """Manages SQLite database for node tracking"""
    
    def __init__(self, db_path: str = "./nodes.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(_thread_local, 'connection'):
            _thread_local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            _thread_local.connection.row_factory = sqlite3.Row
        return _thread_local.connection
    
    def _initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    node_num INTEGER,
                    short_name TEXT,
                    long_name TEXT,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    last_seen_utc TEXT,
                    first_seen_utc TEXT,
                    total_packets_received INTEGER DEFAULT 0,
                    hardware_model TEXT,
                    firmware_version TEXT,
                    is_mqtt BOOLEAN DEFAULT 0,
                    battery_level INTEGER,
                    voltage REAL,
                    is_charging BOOLEAN,
                    is_powered BOOLEAN,
                    last_battery_update_utc TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create packet_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packet_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    received_at_utc TEXT NOT NULL,
                    packet_type TEXT,
                    channel_index INTEGER,
                    hop_start INTEGER,
                    hop_limit INTEGER,
                    hops_away INTEGER,
                    via_mqtt BOOLEAN DEFAULT 0,
                    relay_node_id TEXT,
                    relay_node_name TEXT,
                    rx_snr REAL,
                    rx_rssi INTEGER,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    battery_level INTEGER,
                    voltage REAL,
                    is_charging BOOLEAN,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    message_text TEXT,
                    raw_packet TEXT,
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
                )
            """)
            
            # Create network_topology table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_topology (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_node_id TEXT NOT NULL,
                    neighbor_node_id TEXT NOT NULL,
                    first_heard_utc TEXT NOT NULL,
                    last_heard_utc TEXT NOT NULL,
                    total_packets INTEGER DEFAULT 0,
                    avg_snr REAL,
                    avg_rssi REAL,
                    min_snr REAL,
                    max_snr REAL,
                    min_rssi REAL,
                    max_rssi REAL,
                    link_quality_score REAL,
                    is_active BOOLEAN DEFAULT 1,
                    last_hop_count INTEGER,
                    UNIQUE(source_node_id, neighbor_node_id),
                    FOREIGN KEY (source_node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY (neighbor_node_id) REFERENCES nodes(node_id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_packet_node ON packet_history(node_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_packet_time ON packet_history(received_at_utc)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_topology_source ON network_topology(source_node_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_topology_neighbor ON network_topology(neighbor_node_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_topology_active ON network_topology(is_active)")
            
            conn.commit()
            logger.infogreen("Node tracking database initialized successfully")
            
        except Exception as e:
            logger.warn(f"Failed to initialize database: {e}")
            raise
    
    def upsert_node(self, node_data: Dict[str, Any]) -> bool:
        """Insert or update node information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            node_id = node_data.get('node_id')
            
            # Check if node exists
            cursor.execute("SELECT node_id, first_seen_utc FROM nodes WHERE node_id = ?", (node_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing node
                update_fields = []
                update_values = []
                
                for field in ['node_num', 'short_name', 'long_name', 'latitude', 'longitude', 
                             'altitude', 'hardware_model', 'firmware_version', 'is_mqtt',
                             'battery_level', 'voltage', 'is_charging', 'is_powered']:
                    if field in node_data and node_data[field] is not None:
                        update_fields.append(f"{field} = ?")
                        update_values.append(node_data[field])
                
                # Always update these
                update_fields.extend(['last_seen_utc = ?', 'updated_at = ?', 
                                     'total_packets_received = total_packets_received + 1'])
                update_values.extend([now, now])
                
                # Update battery timestamp if battery data present
                if 'battery_level' in node_data and node_data['battery_level'] is not None:
                    update_fields.append('last_battery_update_utc = ?')
                    update_values.append(now)
                
                update_values.append(node_id)
                
                query = f"UPDATE nodes SET {', '.join(update_fields)} WHERE node_id = ?"
                cursor.execute(query, update_values)
                
            else:
                # Insert new node
                node_data['first_seen_utc'] = now
                node_data['last_seen_utc'] = now
                node_data['created_at'] = now
                node_data['updated_at'] = now
                node_data['total_packets_received'] = 1
                
                if 'battery_level' in node_data and node_data['battery_level'] is not None:
                    node_data['last_battery_update_utc'] = now
                
                fields = list(node_data.keys())
                placeholders = ','.join(['?' for _ in fields])
                query = f"INSERT INTO nodes ({','.join(fields)}) VALUES ({placeholders})"
                cursor.execute(query, [node_data[f] for f in fields])
                
                logger.infogreen(f"New node discovered: {node_id} ({node_data.get('long_name', 'Unknown')})")
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.warn(f"Failed to upsert node {node_id}: {e}")
            return False
    
    def insert_packet(self, packet_data: Dict[str, Any], max_packets_per_node: int = 1000) -> bool:
        """Insert packet history and cleanup old packets if needed"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert packet
            fields = list(packet_data.keys())
            placeholders = ','.join(['?' for _ in fields])
            query = f"INSERT INTO packet_history ({','.join(fields)}) VALUES ({placeholders})"
            cursor.execute(query, [packet_data[f] for f in fields])
            
            # Check packet count for this node
            node_id = packet_data['node_id']
            cursor.execute("SELECT COUNT(*) as count FROM packet_history WHERE node_id = ?", (node_id,))
            count = cursor.fetchone()['count']
            
            # Delete oldest packets if over limit
            if count > max_packets_per_node:
                delete_count = count - max_packets_per_node
                cursor.execute("""
                    DELETE FROM packet_history 
                    WHERE id IN (
                        SELECT id FROM packet_history 
                        WHERE node_id = ? 
                        ORDER BY received_at_utc ASC 
                        LIMIT ?
                    )
                """, (node_id, delete_count))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.warn(f"Failed to insert packet: {e}")
            return False
    
    def update_topology(self, source_id: str, neighbor_id: str, 
                       snr: Optional[float] = None, rssi: Optional[int] = None,
                       hop_count: Optional[int] = None) -> bool:
        """Update network topology information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            # Check if link exists
            cursor.execute("""
                SELECT id, total_packets, avg_snr, avg_rssi, min_snr, max_snr, min_rssi, max_rssi
                FROM network_topology 
                WHERE source_node_id = ? AND neighbor_node_id = ?
            """, (source_id, neighbor_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing link
                total_packets = existing['total_packets'] + 1
                
                # Calculate running averages and min/max
                if snr is not None:
                    avg_snr = ((existing['avg_snr'] or 0) * existing['total_packets'] + snr) / total_packets
                    min_snr = min(existing['min_snr'] or snr, snr)
                    max_snr = max(existing['max_snr'] or snr, snr)
                else:
                    avg_snr = existing['avg_snr']
                    min_snr = existing['min_snr']
                    max_snr = existing['max_snr']
                
                if rssi is not None:
                    avg_rssi = ((existing['avg_rssi'] or 0) * existing['total_packets'] + rssi) / total_packets
                    min_rssi = min(existing['min_rssi'] or rssi, rssi)
                    max_rssi = max(existing['max_rssi'] or rssi, rssi)
                else:
                    avg_rssi = existing['avg_rssi']
                    min_rssi = existing['min_rssi']
                    max_rssi = existing['max_rssi']
                
                # Calculate link quality score
                quality = self._calculate_link_quality(avg_snr, avg_rssi, total_packets)
                
                cursor.execute("""
                    UPDATE network_topology SET
                        last_heard_utc = ?,
                        total_packets = ?,
                        avg_snr = ?,
                        avg_rssi = ?,
                        min_snr = ?,
                        max_snr = ?,
                        min_rssi = ?,
                        max_rssi = ?,
                        link_quality_score = ?,
                        is_active = 1,
                        last_hop_count = ?
                    WHERE source_node_id = ? AND neighbor_node_id = ?
                """, (now, total_packets, avg_snr, avg_rssi, min_snr, max_snr, 
                      min_rssi, max_rssi, quality, hop_count, source_id, neighbor_id))
            else:
                # Insert new link
                quality = self._calculate_link_quality(snr, rssi, 1)
                cursor.execute("""
                    INSERT INTO network_topology (
                        source_node_id, neighbor_node_id, first_heard_utc, last_heard_utc,
                        total_packets, avg_snr, avg_rssi, min_snr, max_snr, min_rssi, max_rssi,
                        link_quality_score, is_active, last_hop_count
                    ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (source_id, neighbor_id, now, now, snr, rssi, snr, snr, rssi, rssi, quality, hop_count))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.warn(f"Failed to update topology: {e}")
            return False
    
    def _calculate_link_quality(self, snr: Optional[float], rssi: Optional[int], 
                                packet_count: int) -> float:
        """Calculate link quality score (0-100)"""
        score = 0.0
        
        # SNR component (40%)
        if snr is not None:
            # SNR typically ranges from -20 to +20 dB
            # Map to 0-100 scale
            snr_normalized = min(100, max(0, (snr + 20) * 2.5))
            score += snr_normalized * 0.4
        
        # RSSI component (40%)
        if rssi is not None:
            # RSSI typically ranges from -120 to -30 dBm
            # Map to 0-100 scale
            rssi_normalized = min(100, max(0, (rssi + 120) * 1.11))
            score += rssi_normalized * 0.4
        
        # Reliability component (20%)
        # More packets = more reliable
        reliability = min(100, packet_count * 2)
        score += reliability * 0.2
        
        return round(score, 2)
    
    def mark_inactive_links(self, timeout_minutes: int = 60):
        """Mark links as inactive if not heard recently"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            timeout_time = (datetime.utcnow() - timedelta(minutes=timeout_minutes)).isoformat()
            
            cursor.execute("""
                UPDATE network_topology 
                SET is_active = 0 
                WHERE last_heard_utc < ? AND is_active = 1
            """, (timeout_time,))
            
            conn.commit()
            
        except Exception as e:
            logger.warn(f"Failed to mark inactive links: {e}")
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes with their information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM nodes ORDER BY last_seen_utc DESC")
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.warn(f"Failed to get nodes: {e}")
            return []
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get specific node information"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            
            return dict(row) if row else None
            
        except Exception as e:
            logger.warn(f"Failed to get node {node_id}: {e}")
            return None
    
    def get_node_packets(self, node_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get packet history for a node"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM packet_history 
                WHERE node_id = ? 
                ORDER BY received_at_utc DESC 
                LIMIT ?
            """, (node_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.warn(f"Failed to get packets for {node_id}: {e}")
            return []
    
    def get_topology(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get network topology data"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute("SELECT * FROM network_topology WHERE is_active = 1")
            else:
                cursor.execute("SELECT * FROM network_topology")
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.warn(f"Failed to get topology: {e}")
            return []
    
    def get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all neighbors (direct connections) for a node"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM network_topology 
                WHERE (source_node_id = ? OR neighbor_node_id = ?) 
                AND is_active = 1
            """, (node_id, node_id))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.warn(f"Failed to get neighbors for {node_id}: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall network statistics"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Node count
            cursor.execute("SELECT COUNT(*) as count FROM nodes")
            stats['total_nodes'] = cursor.fetchone()['count']
            
            # Active nodes (seen in last hour)
            one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            cursor.execute("SELECT COUNT(*) as count FROM nodes WHERE last_seen_utc > ?", (one_hour_ago,))
            stats['active_nodes'] = cursor.fetchone()['count']
            
            # Total packets
            cursor.execute("SELECT COUNT(*) as count FROM packet_history")
            stats['total_packets'] = cursor.fetchone()['count']
            
            # Active links
            cursor.execute("SELECT COUNT(*) as count FROM network_topology WHERE is_active = 1")
            stats['active_links'] = cursor.fetchone()['count']
            
            # Average link quality
            cursor.execute("SELECT AVG(link_quality_score) as avg FROM network_topology WHERE is_active = 1")
            result = cursor.fetchone()
            stats['avg_link_quality'] = round(result['avg'], 2) if result['avg'] else 0
            
            return stats
            
        except Exception as e:
            logger.warn(f"Failed to get statistics: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if hasattr(_thread_local, 'connection'):
            _thread_local.connection.close()
            delattr(_thread_local, 'connection')