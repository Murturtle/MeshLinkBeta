# Absolute Time Scheduling Feature

The MeshLink scheduler now supports **absolute time scheduling** in addition to interval-based scheduling. This allows you to send messages at specific times on specific days of the week.

## New Features

### 1. Timezone Support
You can now specify a timezone for the scheduler. All scheduled times will use this timezone.

```json
{
  "timezone": "US/Central",
  ...
}
```

**Common timezone strings:**
- `US/Central` - Central Time (US)
- `US/Eastern` - Eastern Time (US)
- `US/Mountain` - Mountain Time (US)
- `US/Pacific` - Pacific Time (US)
- `America/Chicago` - Chicago (same as US/Central)
- `America/New_York` - New York (same as US/Eastern)
- `UTC` - Coordinated Universal Time

### 2. Absolute Time Scheduling
Messages can now be scheduled for specific days and times instead of just intervals.

**Format:** `"schedule": "Day Time"`

**Supported formats:**
- `"Sunday 7:30pm"` - 12-hour format with am/pm
- `"Sun 7:30pm"` - Abbreviated day name
- `"Sunday 19:30"` - 24-hour format
- `"7:30pm Sunday"` - Time first, then day

**Day names:**
- Full: `Monday`, `Tuesday`, `Wednesday`, `Thursday`, `Friday`, `Saturday`, `Sunday`
- Abbreviated: `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`

## Configuration Examples

### Example 1: Sunday Net Reminder
Send a reminder at 7:30pm Central on Sundays:

```json
{
  "id": "sunday-net-reminder",
  "text": "Mesh Net is starting in 30 minutes",
  "schedule": "Sunday 7:30pm",
  "enabled": true
}
```

### Example 2: Weekly Check-in
Send a weekly check-in at 9:00am Central on Mondays:

```json
{
  "id": "weekly-check",
  "text": "Weekly mesh network check - All systems go!",
  "schedule": "Monday 9:00am",
  "enabled": true
}
```

### Example 3: Friday Evening Message
Send a message at 6:00pm Central on Fridays:

```json
{
  "id": "friday-evening",
  "text": "Happy Friday! Weekend mesh ops starting soon.",
  "schedule": "Friday 6:00pm",
  "enabled": true
}
```

## Complete Configuration File Example

```json
{
  "enabled": true,
  "check_interval_seconds": 60,
  "log_stats_interval_minutes": 60,
  "persist_stats": false,
  "stats_file": "scheduler_stats.json",
  "timezone": "US/Central",
  "messages": [
    {
      "id": "status-beacon",
      "text": "Automated status beacon - System operational",
      "interval": "30 minutes",
      "enabled": true
    },
    {
      "id": "sunday-net-reminder",
      "text": "Mesh Net is starting in 30 minutes",
      "schedule": "Sunday 7:30pm",
      "enabled": true
    },
    {
      "id": "monday-checkin",
      "text": "Weekly mesh network check - All systems go!",
      "schedule": "Monday 9:00am",
      "enabled": true
    }
  ]
}
```

## How It Works

1. **Interval-based messages** (using `"interval"`) continue to work as before:
   - Send at regular intervals (e.g., every 30 minutes, every 24 hours)
   - First send happens immediately when scheduler starts

2. **Scheduled messages** (using `"schedule"`) work differently:
   - Send at a specific time on a specific day of the week
   - Repeats weekly at the same time
   - First send only happens when the scheduled time arrives

3. **Next send time calculation:**
   - The scheduler calculates when the next occurrence will be
   - Takes into account the current day and time
   - Always schedules for the next upcoming occurrence

## Testing the Configuration

Run the test suite to verify your configuration:

```bash
python3 test_absolute_scheduler.py
```

This will test:
- Schedule string parsing
- Next scheduled time calculation
- Configuration file loading

## Example Use Cases

1. **Net Check-ins**: Scheduled net check-ins at specific times
   ```json
   {
     "schedule": "Sunday 7:00pm",
     "text": "Sunday evening net starting now"
   }
   ```

2. **Weekly Reminders**: Send reminders before scheduled events
   ```json
   {
     "schedule": "Sunday 6:30pm",
     "text": "Net starting in 30 minutes"
   }
   ```

3. **Daily Morning Announcements**: Start-of-day messages
   ```json
   {
     "schedule": "Monday 8:00am",
     "text": "Good morning! Mesh network operational"
   }
   ```

4. **Weekend Operations**: Weekend-specific messages
   ```json
   {
     "schedule": "Saturday 10:00am",
     "text": "Weekend operations - Check your nodes"
   }
   ```

## Logging and Statistics

The scheduler logs will show both interval and scheduled messages:

```
=== Scheduled Messages ===
  status-beacon: every 30m
  sunday-net-reminder: Sunday 7:30pm
  weekly-check: Monday 9:00am
```

Statistics include next send time for scheduled messages:

```
Message Details:
  sunday-net-reminder: 5 sends | Next: Sun 19:30 (3d 7h 13m)
  weekly-check: 12 sends | Next: Mon 09:00 (4d 20h 43m)
```

## Important Notes

1. **Check interval**: The `check_interval_seconds` determines how frequently the scheduler checks if messages should be sent. For scheduled messages, keep this at 60 seconds or less for accuracy.

2. **Timezone matters**: All scheduled times use the configured timezone. Make sure your timezone is set correctly!

3. **First run**: Scheduled messages will NOT send immediately when the scheduler starts (unlike interval messages). They will only send when their scheduled time arrives.

4. **Weekly repeat**: Scheduled messages repeat every week at the same time. There's no way to schedule a one-time message.

## Upgrading from Interval-Only Configuration

If you have an existing `scheduled_messages.json` file:

1. Add the `"timezone"` field at the top level
2. Your existing interval-based messages will continue to work unchanged
3. Add new scheduled messages as needed

Example upgrade:
```json
{
  "enabled": true,
  "timezone": "US/Central",  // ADD THIS LINE
  "messages": [
    // Your existing messages work as-is
    {
      "interval": "30 minutes",
      ...
    },
    // Add new scheduled messages
    {
      "schedule": "Sunday 7:30pm",
      ...
    }
  ]
}
```
