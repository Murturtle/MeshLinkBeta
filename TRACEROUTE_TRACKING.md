# Traceroute Packet Tracking - Implementation Summary

## Overview
MeshLink now tracks TRACEROUTE_APP packets to build detailed network topology maps showing complete packet routes through the mesh network.

## What Was Implemented

### 1. Configuration
- Added `'TRACEROUTE_APP'` to default `track_packet_types`
- Traceroute packets are now stored in `packet_history` table
- Traceroute data is automatically processed when received

### 2. Traceroute Processing (`_process_traceroute()`)

When a traceroute packet is received:

1. **Extract Route Data**
   - Gets the `route` array from the traceroute packet
   - Route contains node numbers for each hop

2. **Convert Node Numbers to IDs**
   - Looks up each node number in the interface's node database
   - Gets the full node ID (e.g., `!a1b2c3d4`)
   - Falls back to constructing ID from node number if not found

3. **Create Topology Links**
   - For each consecutive pair of nodes in the route
   - Creates a topology link in the `network_topology` table
   - Each hop is treated as a direct 1-hop connection
   - Stores SNR data if available in the traceroute

4. **Update Database**
   - Uses existing `update_topology()` method
   - Links are bidirectional and tracked over time
   - Link quality scores are calculated

### 3. Example Traceroute Processing

**Traceroute packet route:**
```
[nodeA, nodeB, nodeC, nodeD]
```

**Creates topology links:**
- nodeA → nodeB (1 hop)
- nodeB → nodeC (1 hop)
- nodeC → nodeD (1 hop)

**Log output:**
```
Processing traceroute with 4 hops
  Traceroute hop 1: !a1b2c3d4 -> !b2c3d4e5
  Traceroute hop 2: !b2c3d4e5 -> !c3d4e5f6
  Traceroute hop 3: !c3d4e5f6 -> !d4e5f6g7
Traceroute processed: c3d4 -> d4e5 -> e5f6 -> f6g7
```

## Benefits

### 1. **Complete Path Visibility**
- Before: Only knew `source → [unknown] → us`
- Now: Know `source → nodeA → nodeB → nodeC → us`

### 2. **Accurate Topology**
- Maps actual packet routes, not inferred connections
- Shows which nodes can directly communicate
- Reveals hidden relay relationships

### 3. **Multi-Hop Routes**
- Tracks entire paths through the network
- Identifies intermediate relay nodes
- Shows route efficiency (actual vs optimal)

### 4. **Network Analysis**
- Find network bottlenecks (heavily-used relay nodes)
- Identify critical nodes
- Discover alternative routes
- Measure route stability over time

## Topology Graph Impact

The topology graph will now show:

1. **Traceroute-Discovered Links**
   - Direct connections between nodes revealed by traceroutes
   - Not just our direct connections, but connections between other nodes

2. **Improved Clustering**
   - Better understanding of which nodes are neighbors
   - More accurate relay relationship mapping

3. **Complete Network Map**
   - Shows full mesh topology
   - Not just hub-and-spoke from our node
   - Reveals the actual mesh structure

## How Traceroute Data is Used

### In Packet History
- Stored in `packet_history` table
- `packet_type`: 'TRACEROUTE_APP'
- `message_text`: "Traceroute: N hops"
- `raw_packet`: Full JSON including route data

### In Network Topology
- Each hop creates/updates a link in `network_topology` table
- Links show:
  - Source node → Target node
  - SNR/RSSI (if available)
  - Hop count: 1 (each traceroute hop is direct)
  - Last heard time
  - Total packets seen on this link

### In Web Visualization
- Graph automatically includes traceroute-discovered links
- Shows connections between nodes beyond just our direct connections
- Reveals the true mesh network structure

## Triggering Traceroutes

To get traceroute data, you need to:

1. **Manual Traceroute**
   - Use Meshtastic app to send traceroute request
   - Target a specific node
   - Response will be processed automatically

2. **Automated Traceroutes** (if implemented in your mesh)
   - Some nodes may periodically run traceroutes
   - Responses will be captured and processed

3. **Network Analysis**
   - Run traceroutes to various nodes
   - Build complete topology map over time

## Data Structure

### Traceroute Packet Structure
```json
{
  "decoded": {
    "portnum": "TRACEROUTE_APP"
  },
  "trace": {
    "route": [
      1127943216,  // Node numbers in the route
      784410078
    ],
    "snrTowards": [24, -12, -47],  // SNR towards destination at each hop
    "routeBack": [1127943216],      // Route back to source
    "snrBack": [-11, 29]            // SNR on return path
  }
}
```

### Topology Link Created
```sql
INSERT INTO network_topology (
  source_node_id,
  neighbor_node_id,
  hop_count,
  avg_snr,
  ...
) VALUES (
  '!a1b2c3d4',
  '!b2c3d4e5',
  1,
  8.5,
  ...
);
```

## Next Steps

To maximize traceroute benefits:

1. **Run Regular Traceroutes**
   - Periodically traceroute to distant nodes
   - Build complete network map

2. **Monitor Topology Changes**
   - Watch how routes change over time
   - Identify unstable links

3. **Analyze Network Health**
   - Find bottleneck nodes
   - Identify critical infrastructure
   - Plan network improvements

## Verification

After restarting MeshLink, check the logs for:

```
Processing traceroute with N hops
  Traceroute hop 1: !xxx -> !yyy
  Traceroute hop 2: !yyy -> !zzz
Traceroute processed: xxx -> yyy -> zzz
```

Check the topology graph - you should see new connections between nodes that were discovered via traceroutes!
