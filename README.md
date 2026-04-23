# Nightreign 遗物合法性查询工具 / Nightreign Relic Legality Inspector

[中文](#中文) | [English](#english)

---

## 中文

这是一款高性能、独立运行的桌面工具，用于查询和验证 **艾尔登法环：Nightreign** 存档文件 (`.sl2`) 中的遗物合法性。基于 Python 和 PyQt6 构建，提供现代且原生的使用体验。
## 核心功能

- **高性能响应：** 使用 PyQt6 和多线程异步解析，即便角色拥有数百个遗物，滚动和加载也极其流畅。
- **合法性验证：** 自动检查遗物是否匹配官方预设，或是否符合游戏随机生成规则（词条池、负面效果池、唯一性排他规则等）。
- **现代 UI：** 完美支持 Windows 和 macOS 的系统级 **浅色/深色模式**。
- **智能过滤：** 可快速切换“只显示不合法遗物”或“只显示官方预设”。
- **完全独立：** 打包脚本会将所有游戏数据（CSV/JSON）集成到单个可执行文件中。
- **双语支持：** 支持英文和简体中文。

### 技术原理

#### 1. 数据提取 (Extraction)
程序通过以下步骤从 `.sl2` 存档中提取遗物数据：
- **BND4 解析：** 存档采用 BND4 容器格式，程序首先解析文件头以定位角色存档槽位（通常为前 10 个 Entry）。
- **解密：** 存档数据使用 AES-CBC 模式加密。程序利用内置密钥对数据块进行解密。
- **特征定位：** 在解密后的二进制流中，程序通过特定的“锚点”字节序列（如 `FACE_ANCHOR`）定位角色数据，并扫描特定字节模式来识别遗物项目结构。
- **结构化读取：** 从每个遗物结构中提取物品 ID 以及 4 个槽位的正面（Buff）和负面（Curse）效果 ID。

#### 2. 合法性校验 (Verification)
校验引擎遵循以下逻辑：
- **官方预设校验：** 优先比对 `official_relics.csv`。若 ID 属于官方预设，其词条必须完全符合预设且不可带有任何负面效果。
- **随机生成规则校验：**
    - **池匹配：** 根据遗物 ID 查找 `EquipParamAntique.csv` 中的规则，验证每个词条是否属于该级别对应的 `AttachEffectTableParam.csv` 抽奖池。
    - **数量限制：** 检查正面和负面效果的数量是否超过该遗物阶级允许的最大值。
    - **互斥规则 (Exclusivity)：** 检查 `AttachEffectParam.csv` 中的互斥组。如果同一个互斥组的词条出现多次（例如同时拥有两个同类型的攻击力加成），则判定为不合法。
    - **深层遗物 (Deep Relics)：** 针对深层遗物，额外校验其负面效果是否属于特定的合法诅咒池。
    - **槽位 4 检查：** 根据游戏逻辑，所有遗物的第 4 个槽位必须为空。

---

## English

#### 前置要求
- Python 3.10 或更高版本
- `pip` (Python 包管理器)

#### 环境配置
1. 克隆此仓库或下载源代码。
2. 安装必要的依赖库：
   ```bash
   pip install -r requirements.txt
   ```

### 使用说明

1. 确保你的艾尔登法环存档文件 (`.sl2`) 位于可访问的文件夹内。
2. 启动应用程序：
   ```bash
   python relic_gui.py
   ```
3. 点击 **加载 .sl2 存档** 并选择你的存档文件。
4. 从下拉菜单中选择角色槽位即可查看其对应的遗物列表。

### 编译打包

如果你想创建一个包含自定义图标和所有数据文件的独立 `.exe` (Windows) 或二进制文件 (macOS/Linux)：

#### Windows
运行提供的批处理脚本：
```cmd
build.cmd
```

#### macOS / Linux
运行提供的 Shell 脚本：
```bash
chmod +x build.sh
./build.sh
```
打包后的文件将存放在 `dist/` 文件夹中。

### 项目结构
- `relic_gui.py`: 主图形界面程序。
- `relic_parser.py`: 命令行版本的工具。
- `official_relics.csv`: 官方系统遗物白名单。
- `dictionary.json`: 词条与物品的 ID 到名称映射表。
- `EquipParamAntique.csv`, `AttachEffectTableParam.csv`, `AttachEffectParam.csv`: 用于规则校验的游戏参数文件。

### 免责声明
本工具仅用于教育和实用辅助目的。所有游戏资产和名称均归其各自所有者所有。

---

## English

A high-performance, standalone desktop utility for inspecting and validating the legality of relics in **Elden Ring: Nightreign** save files (`.sl2`). Built with Python and PyQt6 for a modern, native experience.

### Key Features

- **Fast & Responsive:** Rewritten with PyQt6 and background threading to handle hundreds of relics without freezing.
- **Legality Validation:** Automatically checks if relics match official presets or follow valid RNG rolling rules (buff pools, curse pools, exclusivity, etc.).
- **Modern UI:** Supports system-level **Light/Dark Mode** on both Windows and macOS.
- **Smart Filtering:** Quickly isolate "Illegal Only" or "Official Presets Only".
- **Standalone:** The build process bundles all game data (CSV/JSON) into a single executable.
- **Multilingual:** Supports both English and Simplified Chinese.

### Technical Principles

#### 1. Data Extraction
The program extracts relic data from the `.sl2` save file through the following process:
- **BND4 Parsing:** The save file uses the BND4 container format. The program parses the file header to locate individual character slots (typically the first 10 entries).
- **Decryption:** Save data is encrypted using AES-CBC. The program decrypts data blocks using an internal key.
- **Pattern Matching:** In the decrypted binary stream, the program uses specific "anchor" byte sequences (like `FACE_ANCHOR`) to locate character data and scans for specific byte patterns that identify individual relic item structures.
- **Structured Reading:** It extracts the Item ID and the 4 slots of positive (Buff) and negative (Curse) effect IDs from each relic entry.

#### 2. Legality Verification
The verification engine applies the following logic:
- **Official Whitelist:** It first checks against `official_relics.csv`. If an ID belongs to an official system preset, its effects must exactly match the preset, and it must contain zero curses.
- **Random Relic Rules:**
    - **Pool Validation:** Based on the Relic ID, it retrieves rules from `EquipParamAntique.csv` and verifies if each effect ID belongs to the correct lottery pool in `AttachEffectTableParam.csv` for that relic's tier.
    - **Quantity Limits:** It checks if the number of buffs and curses exceeds the maximum allowed for that specific relic class.
    - **Exclusivity Rules:** It cross-references `AttachEffectParam.csv` for exclusivity groups. Multiple effects from the same group (e.g., two different "Attack Power Up" buffs) are flagged as illegal.
    - **Deep Relics:** For Deep Relics, it performs additional validation of curses against a dedicated pool of valid deep relic debuffs.
    - **Slot 4 Check:** Per game logic, the 4th slot of all relics must be empty.

### Installation

#### Prerequisites
- Python 3.10 or higher
- `pip` (Python package manager)

#### Setup
1. Clone this repository or download the source code.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage

1. Place your Elden Ring save file (`.sl2`) in an accessible folder.
2. Run the application:
   ```bash
   python relic_gui.py
   ```
3. Click **Load .sl2 Save** and select your save file.
4. Select a character slot from the dropdown menu to view their relics.

### Building the Executable

To create a standalone `.exe` (Windows) or binary (macOS/Linux) that includes the custom icon and all data files:

#### Windows
Run the provided batch script:
```cmd
build.cmd
```

#### macOS / Linux
Run the provided shell script:
```bash
chmod +x build.sh
./build.sh
```
The output will be located in the `dist/` folder.

### Project Structure
- `relic_gui.py`: The main GUI application.
- `relic_parser.py`: CLI version of the tool.
- `official_relics.csv`: Whitelist for official system relics.
- `dictionary.json`: ID-to-Name mapping for effects and items.
- `EquipParamAntique.csv`, `AttachEffectTableParam.csv`, `AttachEffectParam.csv`: Game parameter files used for rule validation.

### License
This project is for educational and utility purposes only. All game assets and names belong to their respective owners.
