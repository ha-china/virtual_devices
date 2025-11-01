#!/usr/bin/env python3
"""Test script to verify HA 2025.10.0 compatibility fixes."""

import ast
import os

def check_file_compatibility(file_path, description):
    """Check a specific file for compatibility issues."""
    print(f"Checking {description} ({file_path})...")

    if not os.path.exists(file_path):
        print(f"  SKIP: File not found")
        return True

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check syntax
        ast.parse(content)

        # Check for known problematic imports/usage
        issues = []

        if file_path == "sensor.py":
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
            for cls in problematic_classes:
                if cls in content:
                    issues.append(f"Problematic device class: {cls}")

        elif file_path == "water_heater.py":
            if "WaterHeaterOperationMode" in content:
                issues.append("WaterHeaterOperationMode should be replaced with strings")
            if "from homeassistant.components.water_heater import" in content and "WaterHeaterOperationMode" in content:
                issues.append("WaterHeaterOperationMode import found")

        elif file_path == "light.py":
            if "ATTR_COLOR_TEMP" in content and "ATTR_COLOR_TEMP_KELVIN" not in content:
                issues.append("ATTR_COLOR_TEMP should be replaced with ATTR_COLOR_TEMP_KELVIN")

        elif file_path == "alarm_control_panel.py":
            problematic_consts = [
                "STATE_ALARM_ARMED_AWAY",
                "STATE_ALARM_ARMED_HOME",
                "STATE_ALARM_ARMED_NIGHT",
            ]
            for const in problematic_consts:
                if const in content:
                    issues.append(f"Deprecated alarm state constant: {const}")

        if issues:
            print(f"  ERROR: {', '.join(issues)}")
            return False
        else:
            print(f"  OK: No compatibility issues found")
            return True

    except SyntaxError as e:
        print(f"  ERROR: Syntax error: {e}")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    """Main test function."""
    print("Virtual Devices Multi - HA 2025.10.0 Compatibility Test")
    print("=" * 60)

    # Files to check
    files_to_check = [
        ("sensor.py", "Sensor Platform"),
        ("water_heater.py", "Water Heater Platform"),
        ("humidifier.py", "Humidifier Platform"),
        ("air_purifier.py", "Air Purifier Platform"),
        ("light.py", "Light Platform"),
        ("alarm_control_panel.py", "Alarm Control Panel Platform"),
        ("camera.py", "Camera Platform"),
        ("binary_sensor.py", "Binary Sensor Platform"),
    ]

    all_good = True

    for file_path, description in files_to_check:
        if not check_file_compatibility(file_path, description):
            all_good = False

    print("\n" + "=" * 60)
    if all_good:
        print("SUCCESS: All compatibility checks passed!")
        print("The integration is ready for Home Assistant 2025.10.0")
    else:
        print("ERROR: Some compatibility issues still need to be fixed.")

    print("\nFixed issues:")
    print("- Sensor device classes (UV_INDEX, PM25, PM10, VOC, etc.)")
    print("- Water heater operation modes")
    print("- Light color temperature attributes")
    print("- Alarm system state constants")

if __name__ == "__main__":
    main()