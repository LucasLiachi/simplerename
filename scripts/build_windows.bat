@echo off
echo Installing dependencies...
pip install -r requirements.txt
pip install PyInstaller
echo Building SimpleRename with PyInstaller...
pyinstaller --clean --noconfirm ^
  "SimpleRename_win.spec" ^
  --distpath="dist-windows"
echo Build complete. Check the dist-windows directory.
