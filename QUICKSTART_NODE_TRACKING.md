# Node Tracking Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Dependencies

```bash
# Install web server dependencies (optional, only needed for web interface)
pip install flask flask-cors
```

### Step 2: Enable Node Tracking

Edit your `config.yml` file and add:

```yaml
node_tracking:
  enabled: true
  max_packets_per_node: 1000
  database_path: "./nodes.db"
  json_export_path: "./nodes.json"
  auto_export_json: true
  
  web_server:
    enabled: true      # Set to false if you don't want the web interface
    host: "0.0.0.0"
    port: 8080
  
  track_packet_types:
    - "TEXT_MESSAGE_APP"
    - "POSITION_APP"
    - "NODEINFO_APP"
    - "TELEMETRY_APP"
    - "ROUTING_APP"
  
  topology:
    enabled: true
    link_timeout_minutes: 60
    min_packets_for_link: 3
    calculate_link_quality: true
```

### Step 3: Start MeshLink

```bash
cd MeshLinkBeta
python3 main.py
```

You should see:
```
[INFO] Loading node tracking plugin
[INFO] Node tracking database initialized successfully
[INFO] Node tracking web server starting on http://0.0.0.0:8080
[INFO] Node tracking ready - will capture all packets
```

### Step 4: Access Web Interface

Open your web browser and navigate to:
```
http://localhost:8080
```

Or from another device on your network:
```
http://YOUR_IP_ADDRESS:8080
```

## 📊 What You'll See

### Immediately
- **Empty node list** (will populate as packets are received)
- **Statistics at zero** (will update as data comes in)

### After Receiving Packets
- **Node List**: All discovered nodes with their information
- **Network Topology**: Links between nodes
- **Live Statistics**: Updated network metrics
- **Battery Status**: Power information for each node
- **Signal Quality**: SNR/RSSI metrics

## 🎯 Key Features

### Node List Tab
- ✅ Search nodes by name or ID
- ✅ Filter by battery level
- ✅ Sort by various criteria
- ✅ Click "Details" for comprehensive node info

### Network Topology Tab
- ✅ View all network connections
- ✅ Filter by link quality
- ✅ See SNR/RSSI for each link

### Map View Tab
- ✅ See nodes with GPS coordinates
- ✅ Click to view on Google Maps

## 🔧 Troubleshooting

### Web Interface Not Loading

**Problem**: Can't access http://localhost:8080

**Solutions**:
1. Check if Flask is installed: `pip list | grep -i flask`
2. Verify MeshLink is running and shows web server started
3. Try http://127.0.0.1:8080 instead
4. Check firewall settings

### No Nodes Appearing

**Problem**: Web interface works but shows no nodes

**Solutions**:
1. Ensure your radio is connected and receiving packets
2. Check MeshLink console for packet activity
3. Verify `enabled: true` in node_tracking config
4. Wait a few minutes for packets to be received

### Database Errors

**Problem**: Errors about database or SQLite

**Solutions**:
1. Ensure SQLite3 is installed (comes with Python)
2. Check file permissions in MeshLink directory
3. Delete `nodes.db` and restart (will recreate automatically)

## 📁 Files Created

When running, node tracking creates these files:

```
MeshLinkBeta/
├── nodes.db          # SQLite database with all node data
├── nodes.json        # JSON export (if auto_export_json enabled)
└── web/              # Web interface files (already included)
```

## 🔌 Without Web Interface

If you don't want the web interface, set `web_server.enabled: false`. Node tracking will still work and you can:

1. **View JSON export**: Check `nodes.json` for node data
2. **Query database directly**: Use SQLite to query `nodes.db`
3. **Use REST API**: Access via curl or other tools if web server enabled

Example: Query database directly
```bash
sqlite3 nodes.db "SELECT node_id, long_name, battery_level, last_seen_utc FROM nodes ORDER BY last_seen_utc DESC LIMIT 10;"
```

## 📈 Performance Tips

### For Large Networks (50+ nodes)
- Reduce `max_packets_per_node` to 500 or less
- Consider disabling some packet types you don't need
- Increase `link_timeout_minutes` to reduce topology churn

### For Small Networks (< 10 nodes)
- Increase `max_packets_per_node` for more history
- Decrease `min_packets_for_link` to 1 for faster topology detection
- Decrease `link_timeout_minutes` for more responsive link status

## 🎓 Next Steps

1. **Explore the Web Interface**: Check all three tabs (Nodes, Topology, Map)
2. **Review the Documentation**: See `NODE_TRACKING_README.md` for detailed info
3. **Check the Design**: Read `NODE_TRACKING_DESIGN.md` for architecture details
4. **Customize Settings**: Adjust `config.yml` for your specific needs
5. **Export Data**: Use the API to integrate with other tools

## 💡 Pro Tips

- **Auto-refresh**: The web interface refreshes every 30 seconds
- **Click for Details**: Click any node's "Details" button for full information
- **Search is Smart**: Search works on names and node IDs
- **Sort by Activity**: Sort by "Last Seen" to find most active nodes
- **Battery Monitoring**: Use battery filter to quickly find low battery nodes
- **Export Data**: Use `/api/export/json` endpoint for backups

## 🆘 Need Help?

1. Check the console output for error messages
2. Review `NODE_TRACKING_README.md` for detailed troubleshooting
3. Verify your configuration matches the examples
4. Ensure your Meshtastic radio is properly connected

## 🎉 You're All Set!

Your node tracking system is now active and will automatically capture all nodes and packets on your mesh network. Open the web interface and watch your network come to life!