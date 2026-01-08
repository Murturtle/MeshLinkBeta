"""
Federated Uploader Plugin for MeshLinkBeta

This plugin integrates the federated collector system into MeshLinkBeta.
It captures packets and queues them for upload to the central API.

Configuration (config.yml):
    federated_uploader:
        enabled: true
        collector_id: "collector-01"
        db_path: "./federated_outbox.sqlite"
        enqueue_packet_types:
            - TEXT_MESSAGE_APP
            - POSITION_APP
            - NODEINFO_APP
            - TELEMETRY_APP
            - TRACEROUTE_APP
            - ROUTING_APP
"""

import logging
import time
import sys
import os
from typing import Dict, Any, Optional

# Add federated-meshtastic collector to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../federated-meshtastic/collector'))

try:
    from outbox import OutboxManager
except ImportError:
    logging.error("Failed to import OutboxManager. Make sure federated-meshtastic/collector is available.")
    OutboxManager = None

from plugins.base import Base


logger = logging.getLogger(__name__)


class Plugin(Base):
    """Federated uploader plugin for MeshLinkBeta."""

    plugin_name = "federated_uploader"

    def __init__(self):
        """Initialize the federated uploader plugin."""
        super().__init__()

        if OutboxManager is None:
            logger.error("OutboxManager not available. Plugin will not function.")
            return

        # Load config
        config = self.config.get('federated_uploader', {})
        self.enabled = config.get('enabled', False)

        if not self.enabled:
            logger.info("Federated uploader plugin is disabled")
            return

        self.collector_id = config.get('collector_id', 'meshlink-collector')
        self.db_path = config.get('db_path', './federated_outbox.sqlite')
        self.enqueue_types = set(config.get('enqueue_packet_types', [
            'TEXT_MESSAGE_APP',
            'POSITION_APP',
            'NODEINFO_APP',
            'TELEMETRY_APP',
            'TRACEROUTE_APP',
            'ROUTING_APP',
        ]))

        # Initialize outbox manager
        try:
            self.outbox = OutboxManager(self.db_path, self.collector_id)
            logger.info(f"Federated uploader initialized: collector_id='{self.collector_id}'")

            # Log initial stats
            stats = self.outbox.get_stats()
            logger.info(f"Outbox stats: {stats}")

        except Exception as e:
            logger.error(f"Failed to initialize OutboxManager: {e}", exc_info=True)
            self.enabled = False

    def onReceive(self, packet: Dict[str, Any], interface, client):
        """
        Called when a packet is received.

        Args:
            packet: The received packet
            interface: The Meshtastic interface
            client: The Discord client (if enabled)
        """
        if not self.enabled or self.outbox is None:
            return

        try:
            # Extract packet type
            packet_type = None
            if 'decoded' in packet and 'portnum' in packet['decoded']:
                packet_type = packet['decoded']['portnum']

            # Check if we should enqueue this packet type
            if packet_type and packet_type not in self.enqueue_types:
                logger.debug(f"Skipping packet type {packet_type}")
                return

            # Build event data
            event_data = self._build_event_data(packet, interface)

            # Enqueue for upload
            event_id = self.outbox.enqueue('packet', event_data)

            if event_id:
                logger.debug(f"Enqueued packet {packet.get('id')} from {event_data['from_node']}")
            else:
                logger.debug(f"Duplicate packet {packet.get('id')}")

        except Exception as e:
            logger.error(f"Error processing packet for federated upload: {e}", exc_info=True)

    def _build_event_data(self, packet: Dict[str, Any], interface) -> Dict[str, Any]:
        """
        Build event data from MeshLinkBeta packet format.

        Args:
            packet: Raw packet from Meshtastic
            interface: Meshtastic interface (for node lookups)

        Returns:
            Event data dictionary
        """
        # Basic packet info
        event_data = {
            'packet_id': packet.get('id', 0),
            'from_node': f"!{packet.get('from', 0):08x}",
            'to_node': f"!{packet.get('to', 0):08x}",
            'timestamp': time.time(),
            'channel': packet.get('channel', 0),
            'hop_limit': packet.get('hopLimit'),
            'hop_start': packet.get('hopStart'),
        }

        # RX metadata
        if 'rxRssi' in packet:
            event_data['rssi'] = packet['rxRssi']
        if 'rxSnr' in packet:
            event_data['snr'] = packet['rxSnr']

        # Relay information
        if 'viaMqtt' in packet and packet['viaMqtt']:
            event_data['via_mqtt'] = True

        # Relay node (MeshLinkBeta may have already resolved this)
        if 'relayNode' in packet and packet['relayNode']:
            # Could be partial ID or full ID
            relay = packet['relayNode']
            if isinstance(relay, int):
                event_data['relay_node'] = f"!{relay:08x}"
            else:
                event_data['relay_node'] = str(relay)

        # Decoded data
        if 'decoded' in packet:
            decoded = packet['decoded']
            portnum = decoded.get('portnum', '')

            event_data['port_num'] = portnum
            event_data['type'] = portnum

            # Position data
            if portnum == 'POSITION_APP' and 'position' in decoded:
                pos = decoded['position']
                event_data['from_node_info'] = event_data.get('from_node_info', {})
                if 'latitudeI' in pos:
                    event_data['from_node_info']['latitude'] = pos['latitudeI'] / 1e7
                elif 'latitude' in pos:
                    event_data['from_node_info']['latitude'] = pos['latitude']

                if 'longitudeI' in pos:
                    event_data['from_node_info']['longitude'] = pos['longitudeI'] / 1e7
                elif 'longitude' in pos:
                    event_data['from_node_info']['longitude'] = pos['longitude']

                if 'altitude' in pos:
                    event_data['from_node_info']['altitude'] = pos['altitude']

            # Node info
            if portnum == 'NODEINFO_APP' and 'user' in decoded:
                user = decoded['user']
                event_data['from_node_info'] = event_data.get('from_node_info', {})
                event_data['from_node_info'].update({
                    'short_name': user.get('shortName'),
                    'long_name': user.get('longName'),
                    'hardware': user.get('hwModel'),
                    'role': user.get('role'),
                })

            # Telemetry data
            if portnum == 'TELEMETRY_APP' and 'telemetry' in decoded:
                telem = decoded['telemetry']
                if 'deviceMetrics' in telem:
                    metrics = telem['deviceMetrics']
                    event_data['from_node_info'] = event_data.get('from_node_info', {})
                    if 'batteryLevel' in metrics:
                        event_data['from_node_info']['battery_level'] = metrics['batteryLevel']
                    if 'voltage' in metrics:
                        event_data['from_node_info']['voltage'] = metrics['voltage']

            # Text message (for payload type, not content for privacy)
            if portnum == 'TEXT_MESSAGE_APP':
                event_data['has_text'] = True

            # Traceroute
            if portnum == 'TRACEROUTE_APP' and 'route' in decoded:
                # Store traceroute as separate event
                self._enqueue_traceroute(packet, decoded, interface)

        # Try to get node info from interface cache
        from_id = packet.get('fromId') or packet.get('from')
        if from_id and hasattr(interface, 'nodes'):
            node_info = interface.nodes.get(from_id)
            if node_info:
                event_data['from_node_info'] = event_data.get('from_node_info', {})
                if hasattr(node_info, 'user'):
                    user = node_info.user
                    event_data['from_node_info'].update({
                        'short_name': getattr(user, 'shortName', None),
                        'long_name': getattr(user, 'longName', None),
                        'hardware': getattr(user, 'hwModel', None),
                        'role': getattr(user, 'role', None),
                    })
                if hasattr(node_info, 'position'):
                    pos = node_info.position
                    if hasattr(pos, 'latitude') and pos.latitude:
                        event_data['from_node_info']['latitude'] = pos.latitude
                    if hasattr(pos, 'longitude') and pos.longitude:
                        event_data['from_node_info']['longitude'] = pos.longitude
                    if hasattr(pos, 'altitude') and pos.altitude:
                        event_data['from_node_info']['altitude'] = pos.altitude

        return event_data

    def _enqueue_traceroute(self, packet: Dict[str, Any], decoded: Dict[str, Any], interface):
        """
        Enqueue a traceroute event.

        Args:
            packet: Full packet
            decoded: Decoded traceroute data
            interface: Meshtastic interface
        """
        try:
            route = decoded.get('route', [])
            if not route:
                return

            trace_data = {
                'trace_id': f"{packet.get('id', 0)}-{int(time.time())}",
                'source_node': f"!{packet.get('from', 0):08x}",
                'dest_node': f"!{packet.get('to', 0):08x}",
                'timestamp': time.time(),
                'hops': [
                    {
                        'node_id': f"!{node:08x}" if isinstance(node, int) else str(node),
                        'rssi': packet.get('rxRssi'),
                        'snr': packet.get('rxSnr'),
                        'timestamp': time.time(),
                    }
                    for node in route
                ]
            }

            event_id = self.outbox.enqueue('trace_event', trace_data)
            if event_id:
                logger.debug(f"Enqueued traceroute {trace_data['trace_id']}")

        except Exception as e:
            logger.error(f"Error processing traceroute: {e}", exc_info=True)

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get outbox statistics.

        Returns:
            Dictionary with stats or None if disabled
        """
        if not self.enabled or self.outbox is None:
            return None

        try:
            return self.outbox.get_stats()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return None

    def cleanup(self, days: int = 7) -> int:
        """
        Clean up old sent events.

        Args:
            days: Remove events older than this many days

        Returns:
            Number of events removed
        """
        if not self.enabled or self.outbox is None:
            return 0

        try:
            count = self.outbox.cleanup_old_sent(days)
            logger.info(f"Cleaned up {count} old events (older than {days} days)")
            return count
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
