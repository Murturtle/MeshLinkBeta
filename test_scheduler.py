#!/usr/bin/env python3
"""
Test script for scheduled messages plugin
Verifies configuration loading and interval parsing
"""

import json
import sys
import os

# Add parent directory to path to import plugins
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_interval_parsing():
    """Test interval parsing function"""
    print("Testing interval parsing...")
    
    from plugins.scheduled_messages import ScheduledMessageSender
    
    scheduler = ScheduledMessageSender()
    
    test_cases = [
        ("30 seconds", 30),
        ("5 minutes", 300),
        ("2 hours", 7200),
        ("1 day", 86400),
        ("30 SECONDS", 30),  # Case insensitive
        ("1 minute", 60),    # Singular
        ("invalid", None),   # Invalid format
        ("", None),          # Empty string
    ]
    
    passed = 0
    failed = 0
    
    for interval_str, expected in test_cases:
        result = scheduler._parse_interval(interval_str)
        if result == expected:
            print(f"  ✓ '{interval_str}' -> {result} seconds")
            passed += 1
        else:
            print(f"  ✗ '{interval_str}' -> {result} (expected {expected})")
            failed += 1
    
    print(f"\nInterval parsing: {passed} passed, {failed} failed")
    return failed == 0

def test_config_loading():
    """Test configuration file loading"""
    print("\nTesting configuration loading...")
    
    # Check if example config exists
    if not os.path.exists("scheduled_messages-example.json"):
        print("  ✗ scheduled_messages-example.json not found")
        return False
    
    try:
        with open("scheduled_messages-example.json", 'r') as f:
            config = json.load(f)
        
        print(f"  ✓ Example config loaded successfully")
        print(f"  ✓ Contains {len(config.get('messages', []))} example messages")
        
        # Verify required fields
        required_fields = ["enabled", "check_interval_seconds", "messages"]
        for field in required_fields:
            if field in config:
                print(f"  ✓ Field '{field}' present")
            else:
                print(f"  ✗ Field '{field}' missing")
                return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error loading config: {e}")
        return False

def test_plugin_import():
    """Test if plugin can be imported"""
    print("\nTesting plugin import...")
    
    try:
        from plugins.scheduled_messages import ScheduledMessageSender
        print("  ✓ Plugin imported successfully")
        
        scheduler = ScheduledMessageSender()
        print("  ✓ Plugin instantiated successfully")
        
        # Check if required methods exist
        required_methods = ["start", "onConnect", "onDisconnect", "_scheduler_loop"]
        for method in required_methods:
            if hasattr(scheduler, method):
                print(f"  ✓ Method '{method}' exists")
            else:
                print(f"  ✗ Method '{method}' missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error importing plugin: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Scheduled Messages Plugin - Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Plugin Import", test_plugin_import()))
    results.append(("Interval Parsing", test_interval_parsing()))
    results.append(("Config Loading", test_config_loading()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✓ All tests passed! Plugin is ready to use.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())