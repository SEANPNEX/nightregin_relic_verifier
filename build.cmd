@echo off

:: 1. Create a clean virtual environment
echo Creating virtual environment...
python -m venv venv

:: 2. Activate the environment
echo Activating virtual environment...
call venv\Scripts\activate

:: 3. Upgrade pip and install requirements
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Run PyInstaller
echo Building executable...
pyinstaller --noconsole --onefile --name "NightreignRelicInspector" relic_gui.py

:: 5. Instructions
echo -------------------------------------------------------
echo DONE! Your file is located in: dist\NightreignRelicInspector.exe
echo.
echo CRITICAL: Before running the app, copy these files into the 'dist\' folder:
echo  - dictionary.json
echo  - official_relics.csv
echo  - EquipParamAntique.csv
echo  - AttachEffectTableParam.csv
echo  - AttachEffectParam.csv
echo -------------------------------------------------------
pause
