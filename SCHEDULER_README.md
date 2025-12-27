# Scheduled Messages Plugin

The Scheduled Messages plugin automatically sends messages at configured intervals from within the MeshLink virtual environment.

## Features

- ✅ **Interval-based scheduling** - Simple "30 minutes", "2 hours", "1 day" format
- ✅ **Multiple scheduled messages** - Configure as many recurring messages as needed
- ✅ **Statistics tracking** - Monitor message counts and success rates
- ✅ **Automatic startup** - Messages begin sending immediately on connection
- ✅ **Graceful shutdown** - Clean thread termination on disconnect
- ✅ **Error handling** - Continues operation even if individual sends fail

## Setup

### 1. Create Configuration File

Copy the example configuration:
```bash
cp scheduled_messages-example.json scheduled_messages.json
```

### 2. Configure Your Messages

Edit `scheduled_messages.json`:

```json
{
  "enabled": true,
  "check_interval_seconds": 60,
  "log_stats_interval_minutes": 60,
  "persist_stats": false,
  "stats_file": "scheduler_stats.json",
  "messages": [
    {
      "id": "status-beacon",
      "text": "Automated status beacon - System operational",
      "interval": "30 minutes",
      "enabled": true
    },
    {
      "id": "daily-checkin",
      "text": "Daily system check-in",
      "interval": "24 hours",
      "enabled": true
    }
  ]
}
```

### 3. Start MeshLink

The plugin loads automatically when MeshLink starts:

```bash
python main.py
```

## Configuration Options

### Global Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable the entire scheduler |
| `check_interval_seconds` | integer | `60` | How often to check if messages need sending |
| `log_stats_interval_minutes` | integer | `60` | How often to log detailed statistics |
| `persist_stats` | boolean | `false` | Save statistics to JSON file |
| `stats_file` | string | `scheduler_stats.json` | Statistics file location |

### Message Settings

Each message in the `messages` array supports:

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `id` | string | ✅ Yes | Unique identifier for the message |
| `text` | string | ✅ Yes | Message content to send |
| `interval` | string | ✅ Yes | Send interval (e.g., "30 minutes") |
| `enabled` | boolean | No | Enable/disable this message (default: `true`) |

### Supported Intervals

The scheduler supports human-readable interval formats:

- **Seconds**: `"30 seconds"`, `"45 seconds"`
- **Minutes**: `"5 minutes"`, `"30 minutes"`
- **Hours**: `"1 hour"`, `"2 hours"`, `"12 hours"`
- **Days**: `"1 day"`, `"7 days"`

All intervals are case-insensitive and support singular/plural forms.

## How It Works

### Startup Sequence

1. Plugin loads configuration from `scheduled_messages.json`
2. Validates all message intervals and configurations
3. Creates message schedule in memory
4. When mesh connection established, starts background thread
5. First send happens immediately for each message
6. Subsequent sends happen at configured intervals

### Background Thread

- Runs continuously while mesh connection is active
- Checks every `check_interval_seconds` if messages need sending
- Sends messages via the mesh interface
- Tracks statistics and logging
- Stops gracefully on disconnect or shutdown

### Message Tracking

For each scheduled message, the plugin tracks:
- **Last sent time** - When message was last transmitted
- **First sent time** - Initial transmission timestamp
- **Send count** - Total number of successful sends
- **Interval** - Configured send interval in seconds

## Logging

The plugin provides comprehensive logging:

### Startup Logs
```
[INFO] Loading scheduled message sender plugin
[INFO] Loaded configuration from scheduled_messages.json
[INFO] Loaded 2 scheduled message(s)
[INFO] === Scheduled Messages ===
[INFO]   status-beacon: every 30m
[INFO]   daily-checkin: every 24h
[INFO] Starting scheduled message sender thread
```

### Message Send Logs
```
[INFO] Sent scheduled message: status-beacon (#1)
[INFO] Sent scheduled message: status-beacon (#2)
```

### Periodic Statistics
```
[INFO] === Scheduler Statistics ===
[INFO] Uptime: 1h 30m
[INFO] Messages Sent: 3/3 (100% success)
[INFO] Active Schedules: 2
[INFO] 
[INFO] Message Details:
[INFO]   status-beacon: 3 sends | Next: 15m
[INFO]   daily-checkin: 0 sends | Next: 22h 30m
```

### Shutdown Logs
```
[INFO] Stopping scheduled message sender thread
[INFO] === Final Scheduler Statistics ===
[INFO] Total Messages Sent: 48
[INFO] Send Failures: 0
[INFO]   status-beacon: 48 sends
[INFO]   daily-checkin: 2 sends
```

## Statistics

### Real-time Statistics

The plugin tracks:
- **Total messages sent** - Across all scheduled messages
- **Success rate** - Percentage of successful sends
- **Per-message counters** - Individual send counts
- **Uptime** - How long scheduler has been running
- **Next send times** - When each message will send next

### Statistics Persistence

Enable `persist_stats` to save statistics to a JSON file:

```json
{
  "started": "2025-12-27T02:00:00Z",
  "last_updated": "2025-12-27T03:30:00Z",
  "total_sent": 48,
  "messages": {
    "status-beacon": {
      "count": 46,
      "first_sent": "2025-12-27T02:00:00Z",
      "last_sent": "2025-12-27T03:30:00Z"
    },
    "daily-checkin": {
      "count": 2,
      "first_sent": "2025-12-27T02:00:00Z",
      "last_sent": "2025-12-28T02:00:00Z"
    }
  }
}
```

## Mesh Channel

Scheduled messages are sent to the channel configured in your main `config.yml`:

```yaml
send_channel_index: 0  # Scheduled messages use this channel
```

## Disabling Messages

You can disable individual messages without removing them:

```json
{
  "id": "hourly-ping",
  "text": "Hourly ping",
  "interval": "1 hour",
  "enabled": false
}
```

Or disable the entire scheduler:

```json
{
  "enabled": false,
  "messages": [...]
}
```

## Troubleshooting

### Plugin Not Starting

**Check logs for:**
- `"Scheduled messages config file not found"` - Create `scheduled_messages.json`
- `"No valid scheduled messages found"` - Check interval formats
- `"Error parsing JSON config"` - Validate JSON syntax

**Solutions:**
1. Copy example: `cp scheduled_messages-example.json scheduled_messages.json`
2. Validate JSON: Use a JSON validator
3. Check interval formats match supported patterns

### Messages Not Sending

**Check:**
- Is `enabled: true` in the config?
- Is the mesh connection active?
- Are interval formats valid?
- Check logs for error messages

**Debug:**
1. Set `check_interval_seconds: 10` for faster testing
2. Use short intervals like `"1 minute"` for testing
3. Watch console logs for send confirmations

### High Send Failures

**Possible causes:**
- Mesh connection unstable
- Messages too long for mesh network
- Radio not responding

**Solutions:**
1. Check mesh connection stability
2. Shorten message text
3. Increase `check_interval_seconds`
4. Monitor radio connectivity

## Example Configurations

### Status Beacon
```json
{
  "id": "beacon",
  "text": "Node operational - automated beacon",
  "interval": "30 minutes",
  "enabled": true
}
```

### Daily Weather Summary
```json
{
  "id": "weather-summary",
  "text": "Use $weather for current conditions",
  "interval": "24 hours",
  "enabled": true
}
```

### Hourly Time Check
```json
{
  "id": "time-check",
  "text": "Hourly time sync - use $time command",
  "interval": "1 hour",
  "enabled": true
}
```

### Test Message (Short Interval)
```json
{
  "id": "test",
  "text": "Test message every 2 minutes",
  "interval": "2 minutes",
  "enabled": true
}
```

## Best Practices

1. **Start with longer intervals** - Test with 30+ minutes before using shorter intervals
2. **Monitor message counts** - Check statistics to ensure messages aren't too frequent
3. **Keep messages concise** - Shorter messages are more reliable on mesh networks
4. **Use descriptive IDs** - Make message IDs clear and meaningful
5. **Enable statistics logging** - Monitor scheduler health with periodic logs
6. **Test before deploying** - Use short intervals for initial testing

## Integration

The scheduler integrates seamlessly with MeshLink:

- **Uses existing mesh interface** - No additional configuration needed
- **Respects channel settings** - Sends to configured channel
- **Uses standard logging** - Same format as other plugins
- **Auto-loads on startup** - No manual initialization required
- **Graceful shutdown** - Stops cleanly with MeshLink

## Advanced Usage

### Multiple Message Types

Configure different message types for different purposes:

```json
{
  "messages": [
    {
      "id": "status",
      "text": "System: OK",
      "interval": "1 hour",
      "enabled": true
    },
    {
      "id": "reminder",
      "text": "Check battery levels",
      "interval": "6 hours",
      "enabled": true
    },
    {
      "id": "daily-summary",
      "text": "Daily check-in complete",
      "interval": "24 hours",
      "enabled": true
    }
  ]
}
```

### Debugging Configuration

For testing and debugging:

```json
{
  "enabled": true,
  "check_interval_seconds": 10,
  "log_stats_interval_minutes": 1,
  "persist_stats": true,
  "messages": [
    {
      "id": "test",
      "text": "Test message",
      "interval": "1 minute",
      "enabled": true
    }
  ]
}
```

## Support

For issues or questions:
1. Check MeshLink logs for error messages
2. Verify JSON configuration syntax
3. Test with example configuration
4. Review troubleshooting section above
5. Create an issue on the MeshLink repository