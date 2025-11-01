#!/usr/bin/env python3
"""Simple test script to verify sensor fixes."""

import ast
import os

def check_sensor_file():
    """Check sensor.py for potential issues."""
    print("Checking sensor.py file...")

    if not os.path.exists("sensor.py"):
        print("ERROR: sensor.py file not found")
        return False

    with open("sensor.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check for known problematic device classes
    problematic_classes = [
        "SensorDeviceClass.UV_INDEX",
        "SensorDeviceClass.PM25",
        "SensorDeviceClass.PM10",
        "SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS",
        "SensorDeviceClass.ILLUMINANCE",
        "SensorDeviceClass.SIGNAL_STRENGTH",
        "SensorDeviceClass.PRECIPITATION",
        "SensorDeviceClass.WIND_SPEED",
    ]

    issues = []
    for cls in problematic_classes:
        if cls in content:
            issues.append(cls)

    if issues:
        print(f"ERROR: Found problematic device classes: {issues}")
        return False
    else:
        print("OK: No known problematic device classes found")

    # Check syntax
    try:
        ast.parse(content)
        print("OK: Python syntax is correct")
        return True
    except SyntaxError as e:
        print(f"ERROR: Python syntax error: {e}")
        return False

def main():
    """Main test function."""
    print("Virtual Devices Multi - Fix Validation Test")
    print("=" * 50)

    sensor_ok = check_sensor_file()

    print("\n" + "=" * 50)
    if sensor_ok:
        print("SUCCESS: All checks passed!")
        print("Fixed sensor device class compatibility issues.")
    else:
        print("ERROR: Some issues still need to be fixed.")

if __name__ == "__main__":
    main()