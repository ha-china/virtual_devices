#!/usr/bin/env python3
"""Simple test to verify device types are working."""

def test_device_types():
    """Test if device types are properly defined."""
    # 模拟 DEVICE_TYPES 字典
    DEVICE_TYPES = {
        "light": "灯光",
        "switch": "开关",
        "climate": "空调",
        "cover": "窗帘",
        "fan": "风扇",
        "sensor": "传感器",
        "binary_sensor": "二进制传感器",
        "button": "按钮",
        "scene": "场景",
        "media_player": "媒体播放器",
        "vacuum": "扫地机器人",
        "weather": "气象站",
        "camera": "摄像头",
        "lock": "智能门锁",
        "alarm_control_panel": "警报系统",
        "valve": "水阀",
        "water_heater": "热水器",
        "humidifier": "加湿器",
        "air_purifier": "空气净化器",
    }

    print("Device Types Test")
    print("=" * 40)
    print(f"Total device types: {len(DEVICE_TYPES)}")
    print()

    print("All device types:")
    for i, (key, value) in enumerate(DEVICE_TYPES.items(), 1):
        print(f"{i:2d}. {key} -> {value}")

    print()
    print("Testing vol.In format:")

    # Test different formats
    print("1. Original format (dict):")
    print(f"   vol.In({dict(DEVICE_TYPES)})")

    print("2. Keys only format:")
    print(f"   vol.In({list(DEVICE_TYPES.keys())})")

    print("3. Items format:")
    print(f"   vol.In({list(DEVICE_TYPES.items())})")

    print("4. Manual format:")
    manual_choices = {}
    for key, value in DEVICE_TYPES.items():
        manual_choices[key] = value
    print(f"   vol.In({manual_choices})")

if __name__ == "__main__":
    test_device_types()