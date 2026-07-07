#!/bin/bash

# 1. Create a clean virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# 2. Activate the environment
source venv/bin/activate

# 3. Upgrade pip and install requirements
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run PyInstaller with Bundled Assets and Icon
echo "Building standalone executable..."
pyinstaller --noconfirm --noconsole --onefile --clean \
    --name "NightreignRelicInspector" \
    --icon "fav.ico" \
    --add-data "fav.ico:." \
    --add-data "dictionary.json:." \
    --add-data "official_relics.csv:." \
    --add-data "relic_list.csv:." \
    --add-data "EquipParamAntique.csv:." \
    --add-data "AttachEffectTableParam.csv:." \
    --add-data "AttachEffectParam.csv:." \
    relic_gui.py

echo "Building Single Relic Simulator executable..."
pyinstaller --noconfirm --noconsole --onefile --clean \
    --name "NightreignRelicSingle" \
    --icon "fav.ico" \
    --add-data "fav.ico:." \
    --add-data "dictionary.json:." \
    --add-data "official_relics.csv:." \
    --add-data "relic_list.csv:." \
    --add-data "EquipParamAntique.csv:." \
    --add-data "AttachEffectTableParam.csv:." \
    --add-data "AttachEffectParam.csv:." \
    relic_single.py

# 5. Instructions
echo "-------------------------------------------------------"
echo "DONE! Your files are located in dist/:"
echo " - dist/NightreignRelicInspector"
echo " - dist/NightreignRelicSingle"
echo ""
echo "NOTE: All assets and icon are now bundled INSIDE the executables."
echo "You can move the binaries anywhere and they will work standalone."
echo "-------------------------------------------------------"
