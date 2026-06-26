@echo off
REM SimpleRename Windows Build Script
REM Run this script on a Windows machine to create the Windows executable

echo SimpleRename Build Script for Windows
echo ====================================

REM Install requirements
echo Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install PyInstaller

REM Create Windows executable
echo Building Windows executable...
python -m PyInstaller ^
  --clean ^
  --noconfirm ^
  --windowed ^
  --onefile ^
  --icon=resources\icons\simplerename.ico ^
  --name=SimpleRename ^
  --add-data="resources;resources" ^
  --hidden-import=PyQt6 ^
  --hidden-import=PyQt6.QtCore ^
  --hidden-import=PyQt6.QtGui ^
  --hidden-import=PyQt6.QtWidgets ^
  main.py

echo Build complete! Check the dist folder for SimpleRename.exe