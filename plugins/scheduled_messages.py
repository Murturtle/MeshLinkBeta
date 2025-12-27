import plugins
import plugins.liblogger as logger
import cfg
import json
import os
import time
import threading
import re
from datetime import datetime, timedelta


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
            "messages": []
        }
        self.config_file = "scheduled_messages.json"

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

            # Validate and parse messages
            valid_messages = 0
            for msg in self.config.get("messages", []):
                if not msg.get("enabled", True):
                    continue
                
                interval_seconds = self._parse_interval(msg.get("interval", ""))
                if interval_seconds is None:
                    logger.warn(f"Invalid interval for message '{msg.get('id')}': {msg.get('interval')}")
                    continue
                
                self.message_schedule[msg["id"]] = {
                    "text": msg.get("text", ""),
                    "interval_seconds": interval_seconds,
                    "last_sent": None,
                    "first_sent": None,
                    "send_count": 0,
                    "enabled": True
                }
                valid_messages += 1

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

    def _log_schedule_info(self):
        """Log information about the loaded schedule"""
        logger.info("=== Scheduled Messages ===")
        for msg_id, data in self.message_schedule.items():
            interval_str = self._format_interval(data["interval_seconds"])
            logger.info(f"  {msg_id}: every {interval_str}")

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
        self.statistics["scheduler_started"] = time.time()
        self.statistics["last_stats_log"] = time.time()
        self.stop_event.clear()
        
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
                
                # Check each scheduled message
                for msg_id, data in self.message_schedule.items():
                    if not data["enabled"]:
                        continue
                    
                    # Check if it's time to send
                    if data["last_sent"] is None:
                        # First send - send immediately
                        self._send_scheduled_message(msg_id, data)
                    elif current_time >= data["last_sent"] + data["interval_seconds"]:
                        # Time to send again
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
        if data["last_sent"] is None:
            return "now"
        
        next_time = data["last_sent"] + data["interval_seconds"]
        seconds_until = next_time - time.time()
        
        if seconds_until <= 0:
            return "now"
        
        return self._format_duration(seconds_until)

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