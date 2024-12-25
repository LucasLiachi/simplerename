from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt if it exists
def read_requirements():
    requirements = []
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return requirements

setup(
    name="simplerename",
    version="0.0.4",
    description="A simple batch file renaming tool",
    author="Lucas Liachi",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4.0",
        "pyinstaller>=5.7.0"
    ],
    entry_points={
        "console_scripts": [
            "simplerename=src.main:main",
        ],
    },
    python_requires=">=3.8",
)

# PyInstaller configuration
def create_pyinstaller_spec():
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SimpleRename',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'  # Add your icon here
)
"""
    with open('simplerename.spec', 'w') as f:
        f.write(spec_content)

if __name__ == '__main__':
    create_pyinstaller_spec()
