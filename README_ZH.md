# Nightreign 遗物合法性查询工具

这是一款高性能、独立运行的桌面工具，用于查询和验证 **艾尔登法环：Nightreign** 存档文件 (`.sl2`) 中的遗物合法性。基于 Python 和 PyQt6 构建，提供现代且原生的使用体验。

## 核心功能

- **高性能响应：** 使用 PyQt6 和多线程异步解析，即便角色拥有数百个遗物，滚动和加载也极其流畅。
- **合法性验证：** 自动检查遗物是否匹配官方预设，或是否符合游戏随机生成规则（词条池、负面效果池、唯一性排他规则等）。
- **现代 UI：** 完美支持 Windows 和 macOS 的系统级 **浅色/深色模式**。
- **智能过滤：** 可快速切换“只显示不合法遗物”或“只显示官方预设”。
- **完全独立：** 打包脚本会将所有游戏数据（CSV/JSON）集成到单个可执行文件中。
- **双语支持：** 支持英文和简体中文。

## 安装指南

### 前置要求
- Python 3.10 或更高版本
- `pip` (Python 包管理器)

### 环境配置
1. 克隆此仓库或下载源代码。
2. 安装必要的依赖库：
   ```bash
   pip install -r requirements.txt
   ```

## 使用说明

1. 确保你的艾尔登法环存档文件 (`.sl2`) 位于可访问的文件夹内。
2. 启动应用程序：
   ```bash
   python relic_gui.py
   ```
3. 点击 **加载 .sl2 存档** 并选择你的存档文件。
4. 从下拉菜单中选择角色槽位即可查看其对应的遗物列表。

## 编译打包

如果你想创建一个包含自定义图标和所有数据文件的独立 `.exe` (Windows) 或二进制文件 (macOS/Linux)：

### Windows
运行提供的批处理脚本：
```cmd
build.cmd
```

### macOS / Linux
运行提供的 Shell 脚本：
```bash
chmod +x build.sh
./build.sh
```
打包后的文件将存放在 `dist/` 文件夹中。

## 项目结构
- `relic_gui.py`: 主图形界面程序。
- `relic_parser.py`: 命令行版本的工具。
- `official_relics.csv`: 官方系统遗物白名单。
- `dictionary.json`: 词条与物品的 ID 到名称映射表。
- `EquipParamAntique.csv`, `AttachEffectTableParam.csv`, `AttachEffectParam.csv`: 用于规则校验的游戏参数文件。

## 免责声明
本工具仅用于教育和实用辅助目的。所有游戏资产和名称均归其各自所有者所有。
