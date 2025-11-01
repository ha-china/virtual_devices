# Virtual Devices Multi - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![HA Version](https://img.shields.io/badge/HA-2025.10.0+-blue.svg)](https://www.home-assistant.io/)
[![Quality Scale](https://img.shields.io/badge/Quality%20Scale-Silver-orange.svg)](https://hacs.xyz/docs/publishing/quality-guideline)

This is a custom integration compliant with Home Assistant 2025.10.0 standards, allowing you to create virtual devices **with multiple entities under a single device**, ideal for testing, demonstrations, and development purposes.

## 🎯 Core Features

- ✅ **Multi-Entity Device**: Create multiple entities of the same type under one device
- ✅ **Button Support**: Virtual button entities
- ✅ **Template Functionality**: Supports sensor and other entity templates with dynamic value calculation
- ✅ **Graphical Configuration**: Easily add and configure via the web interface
- ✅ **Device Information**: Full device info and entity category support
- ✅ **HA 2025.10.0 Standards**: Uses the latest APIs and best practices
- ✅ **Multi-Language Support**: Chinese and English interfaces
- ✅ **HACS Compatible**: Meets HACS quality standards

## 📦 Supported Device Types (18)

### 🔆 Lights
- Brightness adjustment
- Color temperature adjustment
- RGB color support
- Light effects (rainbow, blink, breathe, etc.)
- Selective feature activation

### 🔌 Switches
- Simple on/off control
- State persistence
- Suitable for various virtual switch scenarios

### 🎮 Buttons
- Generic buttons
- Restart buttons
- Update buttons
- Identify buttons
- Triggers events for automation

### ❄️ Climate
- Temperature control (configurable range)
- Multiple modes (heat, cool, auto, dry, fan)
- Fan speed adjustment (auto, low, medium, high)
- Swing control (vertical, horizontal, all)

### 🪟 Covers
- 8 cover types (curtains, blinds, garage doors, etc.)
- Position control (0-100%)
- Open, close, stop functions

### 💨 Fans
- Speed control (percentage)
- Preset modes (sleep, natural, strong)
- Oscillation
- Direction control (forward/reverse)

### 📊 Sensors
Supports 10 sensor types:
- Temperature, humidity, pressure
- Illuminance, power, energy
- Voltage, current, battery
- Signal strength

### 🚨 Binary Sensors
Supports 13 sensor types:
- Motion, door/window
- Smoke, gas, moisture
- Occupancy, presence, fault
- Safety, sound, vibration

### 📺 Media Players
Supports 6 media player types:
- TV, speaker, receiver
- Streaming device, game console, computer
- Play, pause, stop, track switching
- Volume control, mute, repeat/shuffle
- Media source switching and templates

### 🤖 Vacuums
Full vacuum functionality:
- Clean, pause, stop, return to dock
- Spot cleaning, zone cleaning, room cleaning
- Multiple fan speeds (quiet to turbo)
- Battery monitoring and auto-charging
- Cleaning history and area statistics
- Real-time state simulation and motion detection

### 🌤️ Weather
Complete weather information:
- Real-time conditions and temperature
- Humidity, pressure, wind speed, visibility
- Dew point, UV index, precipitation
- 5-day forecast and air quality index
- Time and season-based smart simulation

### 📹 Cameras
Supports 5 camera types:
- Indoor, outdoor
- Doorbell, PTZ, baby monitor
- Dynamic image generation (multiple resolutions)
- Motion detection and recording
- PTZ control (PTZ models only)
- Night vision and audio support

### 🔒 Locks
Supports 4 lock types:
- Deadbolt, door lock, padlock, smart lock
- Lock/unlock state control
- Access code verification
- Auto-lock and delay settings
- Battery monitoring
- Lock state change events

### 🚨 Alarm Control Panels
Full alarm control functionality:
- Multiple arming modes (home, away, night)
- Password verification and custom length
- Alarm triggering and disarming
- Alarm history
- Real-time monitoring and notifications

### 🚰 Valves
Supports 4 valve types:
- Water, gas, irrigation, zone
- On/off control and position adjustment
- Flow calculation and cumulative stats
- Pressure monitoring and valve state
- Simulated gradual process and feedback

### 🔋 Water Heaters
Supports water heater functionality:
- Temperature control (configurable range)
- Multiple operation modes (electric, gas, solar, heat pump, tankless)
- Preset temperatures and eco modes
- Status monitoring and safety protection

### 💧 Humidifiers
Supports humidifier functionality:
- Humidity control (configurable range)
- Multiple humidification modes (ultrasonic, evaporative, steam, impeller, warm mist)
- Mist level control and timer functions
- Water shortage protection and tank level display

### 🌬️ Air Purifiers
Supports air purifier functionality:
- Automatic air quality adjustment
- Multiple purification modes (HEPA, activated carbon, UV-C, ionic, ozone, hybrid)
- Fan speed control and filter status monitoring
- PM2.5, formaldehyde, VOC and other pollutant detection

### 🎬 Scenes
Supports scene functionality:
- One-trigger for multiple device state changes
- Support for lighting, curtain, climate and other scenes
- Scene recovery and state memory
- Automation integration support

### 🔋 Batteries
Supports battery monitoring:
- Charge percentage
- Charging status
- Health status
- Low battery alerts

## 📥 Installation

### Method 1: Manual Installation
1. Copy the entire `virtual_devices` folder to Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Search for "Virtual Devices Multi" in the integrations page and add it

### Method 2: Via HACS
1. Open HACS
2. Click the top-right menu → Custom repositories
3. Add this repository URL: https://github.com/ha-china/virtual_devices
4. Search for "Virtual Devices Multi"
5. Install and restart HA

## 🚀 Usage Guide

### Adding a Device

1. Go to **Configuration > Devices & Services**
2. Click **Add Integration**
3. Search and select **Virtual Devices Multi**
4. Follow the wizard:
   - **Step 1**: Enter device name, select device type, set entity count
   - **Step 2**: Configure each entity's name and parameters
5. Upon completion, the device and all entities will appear immediately

### Configuration Examples

#### Example 1: Switch Device (3 Switches)
```
Device Name: Living Room Switch Panel
Device Type: Switch
Entity Count: 3

Entity 1: Living Room Main Light
Entity 2: Living Room Ambient Light
Entity 3: Living Room Outlet
```

Result: Creates 1 device with 3 switch entities

#### Example 2: Light Device (4 Lights)
```
Device Name: Bedroom Light Group
Device Type: Light
Entity Count: 4

Entity 1: Bedroom Main Light (Brightness + Color Temp)
Entity 2: Bedside Lamp (Brightness + RGB)
Entity 3: Ambient Light Strip (RGB + Effects)
Entity 4: Night Light (Brightness Only)
```

Result: Creates 1 device with 4 differently configured light entities

#### Example 3: Button Device (5 Buttons)
```
Device Name: Smart Scene Buttons
Device Type: Button
Entity Count: 5

Entity 1: Home Mode
Entity 2: Away Mode
Entity 3: Sleep Mode
Entity 4: Movie Mode
Entity 5: All Off
```

Result: Creates 1 device with 5 button entities

## ⚙️ Advanced Features

### Template Configuration
Template functionality is supported for the following device types:
- Sensors: Dynamic calculation of temperature, humidity, power values
- Binary Sensors: Generate states based on conditions
- Media Players: Template-based media content and states
- Cameras: Dynamic image content generation

### Device Information
Each virtual device includes:
- Manufacturer: Yunuo Intelligence
- Model: Virtual Device Multi-Entity
- Version: 2025.10.0
- Support for custom device names and entity IDs

### Entity Categories
Sensor entities are automatically categorized as diagnostic for easy management.

## 🛠️ Technical Specifications

- **Compatibility**: Home Assistant 2025.10.0+
- **Integration Type**: Device Integration
- **IoT Class**: Local Polling
- **Quality Standard**: HACS Silver Quality
- **Dependencies**: No external dependencies
- **Entity Count**: 1-10 entities per device

## 🔧 Troubleshooting

### Common Issues
1. **Entities not showing**: Ensure device type and entity configuration are correct
2. **Templates not working**: Check template syntax and referenced entities exist
3. **Media player no sound**: Virtual devices don't produce actual audio
4. **Camera no image**: Need to wait for image generation to complete

### Debug Mode
Enable debug logging in Home Assistant configuration:
```yaml
logger:
  logs:
    custom_components.virtual_devices: debug
```

## 📞 Support

- **GitHub Repository**: https://github.com/ha-china/virtual_devices
- **Issue Reporting**: Please submit to GitHub Issues
- **Documentation**: Check Wiki for more usage instructions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Pull Requests are welcome to improve this project! Please ensure:
- Follow existing code style
- Add appropriate tests
- Update relevant documentation