#!/usr/bin/env python3
"""Test script to verify sensor fixes."""

import ast
import os

def check_sensor_file():
    """Check sensor.py for potential issues."""
    print("检查 sensor.py 文件...")

    if not os.path.exists("sensor.py"):
        print("❌ sensor.py 文件不存在")
        return False

    with open("sensor.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否有已知的有问题的设备类
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
        print(f"❌ 发现有问题的设备类: {issues}")
        return False
    else:
        print("✅ 没有发现已知的有问题的设备类")

    # 检查语法
    try:
        ast.parse(content)
        print("✅ Python 语法正确")
        return True
    except SyntaxError as e:
        print(f"❌ Python 语法错误: {e}")
        return False

def check_other_files():
    """Check other platform files."""
    platform_files = [
        "water_heater.py",
        "humidifier.py",
        "air_purifier.py",
        "camera.py",
        "binary_sensor.py",
        "lock.py",
        "alarm_control_panel.py",
        "valve.py",
        "media_player.py",
        "vacuum.py",
        "weather.py",
    ]

    all_good = True

    for file_name in platform_files:
        if os.path.exists(file_name):
            print(f"检查 {file_name}...")
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
                print(f"✅ {file_name} 语法正确")
            except SyntaxError as e:
                print(f"❌ {file_name} 语法错误: {e}")
                all_good = False
            except Exception as e:
                print(f"❌ {file_name} 其他错误: {e}")
                all_good = False
        else:
            print(f"⚠️ {file_name} 不存在")

    return all_good

def main():
    """Main test function."""
    print("Virtual Devices Multi - 修复验证测试")
    print("=" * 50)

    sensor_ok = check_sensor_file()
    others_ok = check_other_files()

    print("\n" + "=" * 50)
    if sensor_ok and others_ok:
        print("✅ 所有文件检查通过！")
        print("修复了传感器设备类兼容性问题。")
    else:
        print("❌ 仍有一些问题需要修复。")

if __name__ == "__main__":
    main()