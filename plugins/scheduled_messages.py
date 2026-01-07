import plugins
import plugins.liblogger as logger
import cfg
import json
import os
import time
import threading
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class ScheduledMessageSender(plugins.Base):
    """
    Scheduled Message Sender Plugin
    Sends messages at configurable intervals from within the virtual environment
    """

    def __init__(self):
        self.interface = None
        self.client = None
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        self.message_schedule = {}
        self.statistics = {
            "scheduler_started": None,
            "total_messages_sent": 0,
            "last_stats_log": None,
            "send_failures": 0,
            "last_failure_time": None
        }
        self.config = {
            "enabled": True,
            "check_interval_seconds": 60,
            "log_stats_interval_minutes": 60,
            "persist_stats": False,
            "stats_file": "scheduler_stats.json",
            "timezone": "UTC",
            "messages": []
        }
        self.config_file = "scheduled_messages.json"
        self.tz = ZoneInfo("UTC")

    def start(self):
        """Initialize the plugin and load configuration"""
        logger.info("Loading scheduled message sender plugin")
        self._load_config()

    def _load_config(self):
        """Load scheduled messages configuration from JSON file"""
        try:
            if not os.path.exists(self.config_file):
                logger.warn(f"Scheduled messages config file not found: {self.config_file}")
                logger.info("Creating default config from example file")
                
                example_file = "scheduled_messages-example.json"
                if os.path.exists(example_file):
                    with open(example_file, 'r') as f:
                        self.config = json.load(f)
                    with open(self.config_file, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    logger.infogreen(f"Created {self.config_file} from example")
                else:
                    logger.warn("Example config file not found, scheduler will not run")
                    self.config["enabled"] = False
                    return
            else:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.infogreen(f"Loaded configuration from {self.config_file}")

            # Set timezone
            try:
                timezone_str = self.config.get("timezone", "UTC")
                self.tz = ZoneInfo(timezone_str)
                logger.info(f"Using timezone: {timezone_str}")
            except Exception as e:
                logger.warn(f"Invalid timezone '{timezone_str}', falling back to UTC: {e}")
                self.tz = ZoneInfo("UTC")

            # Validate and parse messages
            valid_messages = 0
            for msg in self.config.get("messages", []):
                if not msg.get("enabled", True):
                    continue

                # Check if this is an interval-based or absolute time schedule
                if "interval" in msg:
                    # Interval-based scheduling
                    interval_seconds = self._parse_interval(msg.get("interval", ""))
                    if interval_seconds is None:
                        logger.warn(f"Invalid interval for message '{msg.get('id')}': {msg.get('interval')}")
                        continue

                    self.message_schedule[msg["id"]] = {
                        "text": msg.get("text", ""),
                        "type": "interval",
                        "interval_seconds": interval_seconds,
                        "last_sent": None,
                        "first_sent": None,
                        "send_count": 0,
                        "enabled": True
                    }
                    valid_messages += 1

                elif "schedule" in msg:
                    # Absolute time scheduling
                    schedule_data = self._parse_schedule(msg.get("schedule", ""))
                    if schedule_data is None:
                        logger.warn(f"Invalid schedule for message '{msg.get('id')}': {msg.get('schedule')}")
                        continue

                    self.message_schedule[msg["id"]] = {
                        "text": msg.get("text", ""),
                        "type": "scheduled",
                        "day_of_week": schedule_data["day_of_week"],
                        "time_hour": schedule_data["hour"],
                        "time_minute": schedule_data["minute"],
                        "schedule_str": msg.get("schedule"),
                        "last_sent": None,
                        "first_sent": None,
                        "send_count": 0,
                        "enabled": True
                    }
                    valid_messages += 1
                else:
                    logger.warn(f"Message '{msg.get('id')}' has neither 'interval' nor 'schedule'")
                    continue

            if valid_messages > 0:
                logger.infogreen(f"Loaded {valid_messages} scheduled message(s)")
                self._log_schedule_info()
            else:
                logger.warn("No valid scheduled messages found")
                self.config["enabled"] = False

        except json.JSONDecodeError as e:
            logger.warn(f"Error parsing JSON config: {e}")
            self.config["enabled"] = False
        except Exception as e:
            logger.warn(f"Error loading scheduler config: {e}")
            self.config["enabled"] = False

    def _parse_interval(self, interval_str):
        """
        Parse interval string and return seconds
        Supports: "30 seconds", "5 minutes", "2 hours", "1 day"
        Returns None if invalid
        """
        if not interval_str:
            return None

        interval_str = interval_str.lower().strip()
        
        # Match patterns like "30 minutes", "2 hours", etc.
        pattern = r'(\d+)\s*(second|minute|hour|day)s?'
        match = re.match(pattern, interval_str)
        
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        
        return value * multipliers.get(unit, 0)

    def _parse_schedule(self, schedule_str):
        """
        Parse absolute schedule string and return schedule data
        Supports formats:
          - "Sunday 7:30pm" or "Sunday 19:30"
          - "Sun 7:30pm" or "Sun 19:30"
          - "7:30pm Sunday" or "19:30 Sun"
        Returns dict with day_of_week (0-6, Mon=0), hour (0-23), minute (0-59)
        Returns None if invalid
        """
        if not schedule_str:
            return None

        schedule_str = schedule_str.strip()

        # Day of week mapping
        day_names = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }

        # Try to match patterns like "Sunday 7:30pm" or "7:30pm Sunday"
        # Pattern: optional day, time with optional am/pm, optional day
        pattern = r'(?:(\w+)\s+)?(\d{1,2}):(\d{2})(?:\s*([ap]m))?(?:\s+(\w+))?'
        match = re.match(pattern, schedule_str, re.IGNORECASE)

        if not match:
            return None

        day1, hour_str, minute_str, am_pm, day2 = match.groups()

        # Determine which field has the day
        day_str = day1 or day2
        if not day_str:
            return None

        day_str = day_str.lower()
        if day_str not in day_names:
            return None

        day_of_week = day_names[day_str]

        # Parse time
        try:
            hour = int(hour_str)
            minute = int(minute_str)

            # Handle am/pm
            if am_pm:
                am_pm = am_pm.lower()
                if am_pm == 'pm' and hour != 12:
                    hour += 12
                elif am_pm == 'am' and hour == 12:
                    hour = 0

            # Validate
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                return None

            return {
                "day_of_week": day_of_week,
                "hour": hour,
                "minute": minute
            }

        except ValueError:
            return None

    def _log_schedule_info(self):
        """Log information about the loaded schedule"""
        logger.info("=== Scheduled Messages ===")
        for msg_id, data in self.message_schedule.items():
            if data["type"] == "interval":
                interval_str = self._format_interval(data["interval_seconds"])
                logger.info(f"  {msg_id}: every {interval_str}")
            elif data["type"] == "scheduled":
                logger.info(f"  {msg_id}: {data['schedule_str']}")

    def _format_interval(self, seconds):
        """Format seconds as human-readable interval"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d"

    def _get_next_scheduled_time(self, day_of_week, hour, minute):
        """
        Calculate the next occurrence of a scheduled time
        day_of_week: 0-6 (Monday=0, Sunday=6)
        hour: 0-23
        minute: 0-59
        Returns: datetime object in the configured timezone
        """
        now = datetime.now(self.tz)

        # Create a datetime for today at the scheduled time
        scheduled_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Calculate days until the target day of week
        current_day = now.weekday()
        days_ahead = day_of_week - current_day

        # If the day is today but the time has passed, or if the day is in the past this week
        if days_ahead < 0 or (days_ahead == 0 and now >= scheduled_today):
            days_ahead += 7

        # Calculate the next occurrence
        next_time = scheduled_today + timedelta(days=days_ahead)

        return next_time

    def onConnect(self, interface, client):
        """Start the scheduler when connection is established"""
        self.interface = interface
        self.client = client

        if not self.config.get("enabled", False):
            logger.info("Scheduled message sender is disabled")
            return

        if not self.message_schedule:
            logger.warn("No scheduled messages to send")
            return

        # Start the scheduler thread
        logger.infogreen("Starting scheduled message sender thread")
        startup_time = time.time()
        self.statistics["scheduler_started"] = startup_time
        self.statistics["last_stats_log"] = startup_time
        self.stop_event.clear()

        # Initialize last_sent for interval messages to current time
        # This makes them wait the full interval before first send
        for msg_id, data in self.message_schedule.items():
            if data["type"] == "interval" and data["last_sent"] is None:
                data["last_sent"] = startup_time
                logger.info(f"Scheduled '{msg_id}' to send in {self._format_interval(data['interval_seconds'])}")

        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="SchedulerThread",
            daemon=True
        )
        self.scheduler_thread.start()

    def onDisconnect(self, interface, client):
        """Stop the scheduler when connection is lost"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("Stopping scheduled message sender thread")
            self.stop_event.set()
            self.scheduler_thread.join(timeout=5)
            self._log_final_statistics()

    def _scheduler_loop(self):
        """Main scheduler loop running in background thread"""
        logger.info("Scheduler thread started")

        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                now_dt = datetime.now(self.tz)

                # Check each scheduled message
                for msg_id, data in self.message_schedule.items():
                    if not data["enabled"]:
                        continue

                    should_send = False

                    if data["type"] == "interval":
                        # Interval-based scheduling
                        # last_sent is initialized at startup, so first send waits full interval
                        if data["last_sent"] is not None and current_time >= data["last_sent"] + data["interval_seconds"]:
                            should_send = True

                    elif data["type"] == "scheduled":
                        # Absolute time scheduling
                        next_send = self._get_next_scheduled_time(
                            data["day_of_week"],
                            data["time_hour"],
                            data["time_minute"]
                        )

                        # Check if we should send now
                        # Allow a window of +/- check_interval to account for timing
                        check_window = self.config.get("check_interval_seconds", 60)
                        time_diff = abs((next_send - now_dt).total_seconds())

                        if data["last_sent"] is None:
                            # Never sent before - check if it's time
                            if time_diff < check_window:
                                should_send = True
                        else:
                            # Check if we've passed the scheduled time since last send
                            last_sent_dt = datetime.fromtimestamp(data["last_sent"], tz=self.tz)
                            if next_send > last_sent_dt and time_diff < check_window:
                                should_send = True

                    if should_send:
                        self._send_scheduled_message(msg_id, data)

                # Check if it's time to log statistics
                stats_interval = self.config.get("log_stats_interval_minutes", 60) * 60
                if current_time >= self.statistics["last_stats_log"] + stats_interval:
                    self._log_periodic_statistics()
                    self.statistics["last_stats_log"] = current_time

                # Sleep for check interval
                check_interval = self.config.get("check_interval_seconds", 60)
                self.stop_event.wait(check_interval)

            except Exception as e:
                logger.warn(f"Error in scheduler loop: {e}")
                self.stop_event.wait(60)  # Wait before retrying

        logger.info("Scheduler thread stopped")

    def _send_scheduled_message(self, msg_id, data):
        """Send a scheduled message"""
        try:
            if self.interface is None:
                logger.warn("Cannot send scheduled message: no interface available")
                return
            
            # Send the message
            self.interface.sendText(
                data["text"],
                channelIndex=cfg.config["send_channel_index"]
            )
            
            # Update tracking
            current_time = time.time()
            data["last_sent"] = current_time
            if data["first_sent"] is None:
                data["first_sent"] = current_time
            data["send_count"] += 1
            
            # Update statistics
            self.statistics["total_messages_sent"] += 1
            
            # Log the send
            logger.infogreen(f"Sent scheduled message: {msg_id} (#{data['send_count']})")
            
            # Persist statistics if enabled
            if self.config.get("persist_stats", False):
                self._save_statistics()
            
        except Exception as e:
            logger.warn(f"Failed to send scheduled message '{msg_id}': {e}")
            self.statistics["send_failures"] += 1
            self.statistics["last_failure_time"] = time.time()

    def _log_periodic_statistics(self):
        """Log detailed statistics"""
        if self.statistics["scheduler_started"] is None:
            return
        
        uptime_seconds = time.time() - self.statistics["scheduler_started"]
        uptime_str = self._format_uptime(uptime_seconds)
        
        total_sent = self.statistics["total_messages_sent"]
        failures = self.statistics["send_failures"]
        success_rate = ((total_sent - failures) / total_sent * 100) if total_sent > 0 else 100
        
        logger.info("=== Scheduler Statistics ===")
        logger.info(f"Uptime: {uptime_str}")
        logger.info(f"Messages Sent: {total_sent - failures}/{total_sent} ({success_rate:.1f}% success)")
        logger.info(f"Active Schedules: {len([m for m in self.message_schedule.values() if m['enabled']])}")
        logger.info("")
        logger.info("Message Details:")
        
        for msg_id, data in self.message_schedule.items():
            if not data["enabled"]:
                continue
            
            next_send = self._get_next_send_time(data)
            logger.info(f"  {msg_id}: {data['send_count']} sends | Next: {next_send}")

    def _log_final_statistics(self):
        """Log final statistics on shutdown"""
        logger.info("=== Final Scheduler Statistics ===")
        logger.info(f"Total Messages Sent: {self.statistics['total_messages_sent']}")
        logger.info(f"Send Failures: {self.statistics['send_failures']}")
        
        for msg_id, data in self.message_schedule.items():
            logger.info(f"  {msg_id}: {data['send_count']} sends")

    def _get_next_send_time(self, data):
        """Calculate and format next send time"""
        if data["type"] == "interval":
            if data["last_sent"] is None:
                return "not scheduled"

            next_time = data["last_sent"] + data["interval_seconds"]
            seconds_until = next_time - time.time()

            if seconds_until <= 0:
                return "now"

            return self._format_duration(seconds_until)

        elif data["type"] == "scheduled":
            next_dt = self._get_next_scheduled_time(
                data["day_of_week"],
                data["time_hour"],
                data["time_minute"]
            )
            now_dt = datetime.now(self.tz)
            seconds_until = (next_dt - now_dt).total_seconds()

            if seconds_until <= 0:
                return "now"

            # Format the next scheduled time
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            day_name = day_names[data["day_of_week"]]
            time_str = f"{data['time_hour']:02d}:{data['time_minute']:02d}"

            return f"{day_name} {time_str} ({self._format_duration(seconds_until)})"

        return "unknown"

    def _format_duration(self, seconds):
        """Format seconds as human-readable duration"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            return f"{days}d {hours}h"

    def _format_uptime(self, seconds):
        """Format uptime as human-readable string"""
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        minutes = int((seconds % 3600) / 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _save_statistics(self):
        """Save statistics to JSON file"""
        try:
            stats_file = self.config.get("stats_file", "scheduler_stats.json")
            stats_data = {
                "started": datetime.fromtimestamp(self.statistics["scheduler_started"]).isoformat() if self.statistics["scheduler_started"] else None,
                "last_updated": datetime.now().isoformat(),
                "total_sent": self.statistics["total_messages_sent"],
                "send_failures": self.statistics["send_failures"],
                "messages": {}
            }
            
            for msg_id, data in self.message_schedule.items():
                stats_data["messages"][msg_id] = {
                    "count": data["send_count"],
                    "first_sent": datetime.fromtimestamp(data["first_sent"]).isoformat() if data["first_sent"] else None,
                    "last_sent": datetime.fromtimestamp(data["last_sent"]).isoformat() if data["last_sent"] else None
                }
            
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
                
        except Exception as e:
            logger.warn(f"Failed to save statistics: {e}")