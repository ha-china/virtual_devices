# Virtual Devices Multi - 虚拟设备集成（多实体）

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![HA Version](https://img.shields.io/badge/HA-2025.10.0+-blue.svg)](https://www.home-assistant.io/)
[![Quality Scale](https://img.shields.io/badge/Quality%20Scale-Silver-orange.svg)](https://hacs.xyz/docs/publishing/quality-guideline)
[![Code Size](https://img.shields.io/github/languages/code-size/ha-china/virtual_devices?color=green)](https://github.com/ha-china/virtual_devices)
[![Last Commit](https://img.shields.io/github/last-commit/ha-china/virtual_devices?color=blue)](https://github.com/ha-china/virtual_devices)

**Language**: [中文](README_CN.md) | [English](README.md)

这是符合 Home Assistant 2025.10.0 标准的企业级虚拟设备集成，**支持在一个设备下创建多个相同类型的实体**，拥有超过11,000行代码的强大功能，为测试、演示、开发和学习提供完整的IoT设备模拟环境。

## ✨ 核心特性

- 🎯 **一设备多实体**：一个设备包含1-10个相同类型实体，完美模拟真实设备
- 🛠️ **18种设备类型**：覆盖智能家居所有主要设备类别
- 🎨 **图形化配置**：Web界面分步向导，支持批量配置
- 📊 **模板系统**：动态计算传感器数值、媒体内容、图像生成
- 💾 **状态持久化**：自动保存和恢复设备状态
- 🌍 **多语言支持**：完整的中英文界面
- 🔧 **企业级质量**：HACS Silver认证，严格遵循HA规范
- ⚡ **高性能**：异步操作，优化资源使用
- 🎮 **自动化友好**：丰富的事件触发和状态反馈

## 📱 支持的设备类型

### 🏠 核心家居设备

| 设备类型 | 功能特性 | 复杂度 |
|---------|----------|--------|
| 🔆 **灯光** | 亮度/色温/RGB/灯效 | ⭐⭐⭐ |
| 🔌 **开关** | 基础开关/状态持久化 | ⭐ |
| ❄️ **空调** | 温控/多模式/风速/摆风 | ⭐⭐⭐ |
| 🪟 **窗帘** | 8种类型/位置控制 | ⭐⭐ |
| 💨 **风扇** | 变速/模式/摆动/方向 | ⭐⭐ |
| 🚨 **二进制传感器** | 13种状态监测 | ⭐⭐ |

### 🎮 娱乐与通信

| 设备类型 | 功能特性 | 复杂度 |
|---------|----------|--------|
| 📺 **媒体播放器** | 6种类型/播放控制/音量 | ⭐⭐⭐⭐ |
| 🎮 **按钮** | 4种类型/自动化触发 | ⭐ |
| 🎬 **场景** | 多设备联动/状态恢复 | ⭐⭐ |

### 🏥 环境与健康

| 设备类型 | 功能特性 | 复杂度 |
|---------|----------|--------|
| 📊 **传感器** | 16种环境/电力/空气质量监测 | ⭐⭐⭐ |
| 💧 **加湿器** | 5种模式/湿度控制/水位显示 | ⭐⭐⭐⭐ |
| 🌬️ **空气净化器** | 6种净化模式/AQI监测 | ⭐⭐⭐⭐⭐ |
| 🌤️ **气象站** | 完整天气/5天预报 | ⭐⭐⭐ |

### 🛡️ 安全与安防

| 设备类型 | 功能特性 | 复杂度 |
|---------|----------|--------|
| 🤖 **扫地机器人** | 清洁模式/充电/路径规划 | ⭐⭐⭐⭐ |
| 📹 **摄像头** | 5种类型/录制/夜视/PTZ | ⭐⭐⭐⭐⭐ |
| 🔒 **智能门锁** | 4种类型/密码/自动锁定 | ⭐⭐⭐ |
| 🚰 **水阀** | 4种类型/流量控制/位置反馈 | ⭐⭐⭐⭐ |

### 🔧 公共设施

| 设备类型 | 功能特性 | 复杂度 |
|---------|----------|--------|
| 🔋 **热水器** | 5种加热模式/能效管理 | ⭐⭐⭐ |

## 🚀 快速开始

### 安装方法

#### 方法1：通过HACS安装（推荐）
1. 打开 **HACS → 集成**
2. 点击右上角 **菜单 → 自定义存储库**
3. 添加仓库：`https://github.com/ha-china/virtual_devices`
4. 搜索 **"虚拟设备集成（多实体）"** 并安装
5. 重启Home Assistant

#### 方法2：手动安装
1. 下载 [最新版本](https://github.com/ha-china/virtual_devices/releases)
2. 解压到 `config/custom_components/virtual_devices/`
3. 重启Home Assistant

### 添加设备

1. 进入 **设置 → 设备与服务 → 添加集成**
2. 搜索 **"虚拟设备集成（多实体）"**
3. 按照向导完成配置

## 💡 使用场景

### 🧪 开发测试
```yaml
# 测试自动化规则
- alias: "测试灯光场景"
  trigger:
    platform: state
    entity_id: button.test_scene_button
  action:
    service: scene.turn_on
    target:
      entity_id: scene.test_living_room
```

### 🏠 演示展示
```yaml
# 创建完整的智能家居演示
设备名称: 智能展厅设备组
实体数量: 8个
类型: 混合设备展示
```

### 📚 学习教育
```yaml
# Home Assistant学习环境
- 传感器数据模拟
- 自动化规则测试
- UI界面定制
- API接口学习
```

## 🔧 高级功能


### 状态持久化
- 所有设备状态自动保存
- 重启后状态完全恢复
- 支持状态历史查询
- 可配置保存间隔



## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 🐛 报告问题
- 使用 [GitHub Issues](https://github.com/ha-china/virtual_devices/issues)
- 提供详细的错误日志
- 说明复现步骤
- 描述期望行为

### 💡 功能建议
- 在Issues中标记为"enhancement"
- 详细描述功能需求
- 说明使用场景
- 考虑实现可行性

### 🔧 代码贡献
1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 📝 文档改进
- 翻译文档到其他语言
- 改进现有文档内容
- 添加使用示例
- 制作视频教程


## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- **GitHub仓库**: https://github.com/ha-china/virtual_devices
- **问题反馈**: https://github.com/ha-china/virtual_devices/issues
- **功能建议**: https://github.com/ha-china/virtual_devices/discussions
- **更新日志**: [CHANGELOG.md](CHANGELOG.md)
- **API文档**: [WIKI](https://github.com/ha-china/virtual_devices/wiki)

