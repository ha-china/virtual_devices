# Virtual Devices Multi - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![HA Version](https://img.shields.io/badge/HA-2025.10.0+-blue.svg)](https://www.home-assistant.io/)
[![Quality Scale](https://img.shields.io/badge/Quality%20Scale-Silver-orange.svg)](https://hacs.xyz/docs/publishing/quality-guideline)
[![Code Size](https://img.shields.io/github/languages/code-size/ha-china/virtual_devices?color=green)](https://github.com/ha-china/virtual_devices)
[![Last Commit](https://img.shields.io/github/last-commit/ha-china/virtual_devices?color=blue)](https://github.com/ha-china/virtual_devices)

**Language**: [中文](README_CN.md) | [English](README.md)

An enterprise-grade virtual device integration for Home Assistant 2025.10.0+ with **multi-entity device support**. it provides a complete device simulation environment for testing, demonstrations, development, and educational purposes.

## ✨ Core Features

- 🎯 **Multi-Entity Devices**: Create 1-10 entities of the same type under one device
- 🛠️ **20 Device Types**: Cover all major smart home device categories
- 🎨 **Graphical Configuration**: Web-based wizard with step-by-step guidance
- 📊 **Template System**: Dynamic sensor calculations, media content, and image generation
- 💾 **State Persistence**: Automatic save and restore of device states
- 🧺 **Complete Laundry Simulation**: Washer and dryer include program selection, delay start, control buttons, and core runtime sensors
- 🌍 **Multi-Language Support**: Complete Chinese and English interface
- 🔧 **Enterprise Quality**: HACS Silver certified, strict HA standards compliance
- ⚡ **High Performance**: Async operations with optimized resource usage
- 🎮 **Automation Friendly**: Rich event triggers and state feedback

## 📱 Supported Device Types

### 🏠 Core Home Devices

| Device Type | Features | Complexity |
|-------------|----------|------------|
| 🔆 **Light** | Brightness/Color Temp/RGB/Effects | ⭐⭐⭐ |
| 🔌 **Switch** | Basic on/off with state persistence | ⭐ |
| ❄️ **Climate** | Temp control/Multiple modes/Fan speeds | ⭐⭐⭐ |
| 🪟 **Cover** | 8 types with position control | ⭐⭐ |
| 💨 **Fan** | Variable speed/Modes/Oscillation | ⭐⭐ |
| 🚨 **Binary Sensor** | 13 status monitoring types | ⭐⭐ |

### 🎮 Entertainment & Communication

| Device Type | Features | Complexity |
|-------------|----------|------------|
| 📺 **Media Player** | 6 types/Playback control/Volume | ⭐⭐⭐⭐ |
| 🎮 **Button** | 4 types for automation triggers | ⭐ |
| 🎬 **Scene** | Multi-device linkage/State recovery | ⭐⭐ |

### 🏥 Environmental & Health

| Device Type | Features | Complexity |
|-------------|----------|------------|
| 📊 **Sensor** | 16 environmental/power/air quality types | ⭐⭐⭐ |
| 💧 **Humidifier** | 5 modes/Humidity control/Water level | ⭐⭐⭐⭐ |
| 🌬️ **Air Purifier** | 6 purification modes/AQI monitoring | ⭐⭐⭐⭐⭐ |
| 🌤️ **Weather** | Complete weather/5-day forecast | ⭐⭐⭐ |

### 🛡️ Security & Safety

| Device Type | Features | Complexity |
|-------------|----------|------------|
| 🤖 **Vacuum** | Cleaning modes/Charging/Path planning | ⭐⭐⭐⭐ |
| 📹 **Camera** | 5 types/Recording/Night vision/PTZ | ⭐⭐⭐⭐⭐ |
| 🔒 **Lock** | 4 types/Passwords/Auto-lock | ⭐⭐⭐ |
| 🚰 **Valve** | 4 types/Flow control/Position feedback | ⭐⭐⭐⭐ |

### 🔧 Utilities

| Device Type | Features | Complexity |
|-------------|----------|------------|
| 🔋 **Water Heater** | 5 heating modes/Energy management | ⭐⭐⭐ |
| 🧺 **Washer** | Program selection/Delay start/Start-Pause-Resume-Stop/5 core sensors | ⭐⭐⭐⭐ |
| 👕 **Dryer** | Program selection/Drying target/Delay start/5 core sensors | ⭐⭐⭐⭐ |

### 🧺 Laundry Entity Set

Washer and dryer are exposed as complete appliance groups instead of a single toggle. Each configured laundry device can provide:

- `switch`: power control
- `select`: program selection, plus washer temperature/spin speed or dryer drying target
- `button`: start, pause, resume, and stop
- `number`: delay start minutes
- `sensor`: operation state, remaining time, total time, progress, and finish time
- `binary_sensor`: door, remote start, and remote control

## 🚀 Quick Start

### Installation Methods

#### Method 1: HACS Installation (Recommended)
1. Go to **HACS → Integrations**
2. Click **Menu → Custom Repositories**
3. Add repository: `https://github.com/ha-china/virtual_devices`
4. Search for **"Virtual Devices Multi"** and install
5. Restart Home Assistant

#### Method 2: Manual Installation
1. Download the [latest release](https://github.com/ha-china/virtual_devices/releases)
2. Extract to `config/custom_components/virtual_devices/`
3. Restart Home Assistant

### Adding Devices

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **"Virtual Devices Multi"**
3. Follow the configuration wizard

## 💡 Use Cases

### 🧪 Development & Testing
```yaml
# Test automation rules
- alias: "Test Light Scene"
  trigger:
    platform: state
    entity_id: button.test_scene_button
  action:
    service: scene.turn_on
    target:
      entity_id: scene.test_living_room
```

### 🏠 Demonstrations
```yaml
# Complete smart home demo
Device Name: Smart Showroom Devices
Entity Count: 8
Type: Mixed Device Showcase
```

### 📚 Learning & Education
```yaml
# Home Assistant learning environment
- Sensor data simulation
- Automation rule testing
- UI customization
- API interface learning
```

## 🤝 Contributing

We welcome all forms of contributions!

### 🐛 Bug Reports
- Use [GitHub Issues](https://github.com/ha-china/virtual_devices/issues)
- Provide detailed error logs
- Include reproduction steps
- Describe expected behavior

### 💡 Feature Suggestions
- Mark Issues as "enhancement"
- Describe feature requirements in detail
- Explain use cases
- Consider implementation feasibility

### 🔧 Code Contributions
1. Fork the project repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

### 📝 Documentation Improvements
- Translate documentation to other languages
- Improve existing documentation content
- Add usage examples
- Create video tutorials



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 🔗 Related Links

- **GitHub Repository**: https://github.com/ha-china/virtual_devices
- **Issue Reporting**: https://github.com/ha-china/virtual_devices/issues
- **Feature Requests**: https://github.com/ha-china/virtual_devices/discussions
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **API Documentation**: [WIKI](https://github.com/ha-china/virtual_devices/wiki)
