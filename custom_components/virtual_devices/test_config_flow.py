#!/usr/bin/env python3
"""Test script to verify config flow device types."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_device_types():
    """Test if all device types are properly defined."""
    try:
        from const import DEVICE_TYPES, DEVICE_TYPE_WATER_HEATER, DEVICE_TYPE_HUMIDIFIER, DEVICE_TYPE_AIR_PURIFIER

        print("Device Types Test")
        print("=" * 40)

        print(f"Total device types: {len(DEVICE_TYPES)}")

        # Check if new device types are in the dictionary
        new_types = [
            DEVICE_TYPE_WATER_HEATER,
            DEVICE_TYPE_HUMIDIFIER,
            DEVICE_TYPE_AIR_PURIFIER,
        ]

        print("\nChecking new device types:")
        for device_type in new_types:
            if device_type in DEVICE_TYPES:
                print(f"  OK: {device_type} -> {DEVICE_TYPES[device_type]}")
            else:
                print(f"  ERROR: {device_type} not found in DEVICE_TYPES")

        print("\nAll available device types:")
        for device_type, name in DEVICE_TYPES.items():
            print(f"  {device_type}: {name}")

        return True

    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_config_flow_import():
    """Test if config flow can be imported."""
    try:
        import config_flow
        print("\nConfig Flow Import: OK")
        return True
    except ImportError as e:
        print(f"\nConfig Flow Import Error: {e}")
        return False

def main():
    """Main test function."""
    print("Virtual Devices Multi - Config Flow Test")
    print("=" * 50)

    device_types_ok = test_device_types()
    config_flow_ok = test_config_flow_import()

    print("\n" + "=" * 50)
    if device_types_ok and config_flow_ok:
        print("SUCCESS: Config flow appears to be correctly set up")
        print("If device types are not showing in HA, try:")
        print("1. Restart Home Assistant")
        print("2. Clear HA cache")
        print("3. Reinstall the integration")
    else:
        print("ERROR: Some issues found in config flow setup")

if __name__ == "__main__":
    main()