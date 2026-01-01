#!/usr/bin/env python3
"""
Test script for absolute time scheduling feature
"""

import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Add parent directory to path to import plugins
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_schedule_parsing():
    """Test schedule parsing function"""
    print("Testing schedule parsing...")

    from plugins.scheduled_messages import ScheduledMessageSender

    scheduler = ScheduledMessageSender()

    test_cases = [
        ("Sunday 7:30pm", {"day_of_week": 6, "hour": 19, "minute": 30}),
        ("Sun 7:30pm", {"day_of_week": 6, "hour": 19, "minute": 30}),
        ("Sunday 19:30", {"day_of_week": 6, "hour": 19, "minute": 30}),
        ("Monday 9:00am", {"day_of_week": 0, "hour": 9, "minute": 0}),
        ("Mon 9:00am", {"day_of_week": 0, "hour": 9, "minute": 0}),
        ("Friday 12:00pm", {"day_of_week": 4, "hour": 12, "minute": 0}),
        ("Saturday 11:59pm", {"day_of_week": 5, "hour": 23, "minute": 59}),
        ("Wednesday 8:15am", {"day_of_week": 2, "hour": 8, "minute": 15}),
        ("7:30pm Sunday", {"day_of_week": 6, "hour": 19, "minute": 30}),
        ("9:00am Monday", {"day_of_week": 0, "hour": 9, "minute": 0}),
        ("invalid", None),  # Invalid format
        ("25:00 Sunday", None),  # Invalid hour
        ("Sunday 13:70", None),  # Invalid minute
    ]

    passed = 0
    failed = 0

    for schedule_str, expected in test_cases:
        result = scheduler._parse_schedule(schedule_str)
        if result == expected:
            print(f"  ✓ '{schedule_str}' -> {result}")
            passed += 1
        else:
            print(f"  ✗ '{schedule_str}' -> {result} (expected {expected})")
            failed += 1

    print(f"\nSchedule parsing: {passed} passed, {failed} failed")
    return failed == 0


def test_next_scheduled_time():
    """Test next scheduled time calculation"""
    print("\nTesting next scheduled time calculation...")

    from plugins.scheduled_messages import ScheduledMessageSender

    scheduler = ScheduledMessageSender()
    scheduler.tz = ZoneInfo("US/Central")

    now = datetime.now(scheduler.tz)
    print(f"  Current time: {now.strftime('%A %I:%M%p %Z')}")
    print(f"  Current day: {now.weekday()} (0=Monday, 6=Sunday)")

    # Test Sunday 7:30pm
    next_time = scheduler._get_next_scheduled_time(6, 19, 30)  # Sunday 7:30pm
    print(f"  Next 'Sunday 7:30pm': {next_time.strftime('%A %Y-%m-%d %I:%M%p %Z')}")

    # Verify it's in the future
    if next_time > now:
        print(f"  ✓ Next time is in the future")

        # Calculate days until
        days_until = (next_time - now).days
        if days_until == 0:
            print(f"  ✓ Scheduled for today")
        else:
            print(f"  ✓ Scheduled in {days_until} days")
    else:
        print(f"  ✗ Next time is in the past!")
        return False

    # Test Monday 9:00am
    next_time = scheduler._get_next_scheduled_time(0, 9, 0)  # Monday 9:00am
    print(f"  Next 'Monday 9:00am': {next_time.strftime('%A %Y-%m-%d %I:%M%p %Z')}")

    if next_time > now:
        print(f"  ✓ Next time is in the future")
    else:
        print(f"  ✗ Next time is in the past!")
        return False

    print("\n  ✓ Next scheduled time calculation works correctly")
    return True


def test_config_loading():
    """Test configuration loading with new features"""
    print("\nTesting configuration loading with absolute schedules...")

    import json

    try:
        with open("scheduled_messages.json", 'r') as f:
            config = json.load(f)

        print(f"  ✓ Config loaded successfully")

        # Check timezone
        if "timezone" in config:
            print(f"  ✓ Timezone: {config['timezone']}")
        else:
            print(f"  ✗ Timezone field missing")
            return False

        # Count interval vs scheduled messages
        interval_count = sum(1 for m in config['messages'] if 'interval' in m)
        scheduled_count = sum(1 for m in config['messages'] if 'schedule' in m)

        print(f"  ✓ Interval-based messages: {interval_count}")
        print(f"  ✓ Scheduled messages: {scheduled_count}")

        # Display scheduled messages
        if scheduled_count > 0:
            print("\n  Scheduled messages:")
            for msg in config['messages']:
                if 'schedule' in msg:
                    print(f"    - {msg['id']}: {msg['schedule']}")

        return True

    except Exception as e:
        print(f"  ✗ Error loading config: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Absolute Time Scheduling - Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Schedule Parsing", test_schedule_parsing()))
    results.append(("Next Scheduled Time", test_next_scheduled_time()))
    results.append(("Config Loading", test_config_loading()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} test suites passed")

    if passed == total:
        print("\n✓ All tests passed! Absolute scheduling is ready to use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
