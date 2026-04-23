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

# 4. Run PyInstaller with Bundled Assets
echo "Building standalone executable..."
pyinstaller --noconsole --onefile --clean \
    --name "NightreignRelicInspector" \
    --add-data "dictionary.json:." \
    --add-data "official_relics.csv:." \
    --add-data "EquipParamAntique.csv:." \
    --add-data "AttachEffectTableParam.csv:." \
    --add-data "AttachEffectParam.csv:." \
    relic_gui.py

# 5. Instructions
echo "-------------------------------------------------------"
echo "DONE! Your file is located in: dist/NightreignRelicInspector"
echo ""
echo "NOTE: All assets (CSV/JSON) are now bundled INSIDE the executable."
echo "You can move the binary anywhere and it will work standalone."
echo "-------------------------------------------------------"
