from setuptools import setup, find_packages
import os
import subprocess
import sys
import platform
from pathlib import Path

# Read requirements from requirements.txt if it exists
def read_requirements():
    requirements = []
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return requirements

# Configuração do Wine para compilação cross-platform
def setup_wine_environment():
    """Configura o ambiente Wine para compilação cross-platform"""
    if platform.system() != "Linux":
        print("Esta função deve ser executada apenas no Linux/WSL")
        return False
    
    try:
        # Verifica se o Wine está instalado
        wine_version = subprocess.run(
            ["wine", "--version"], 
            capture_output=True, 
            text=True
        )
        if wine_version.returncode != 0:
            print("Wine não encontrado. Instale com: sudo apt install wine64")
            return False
        
        print(f"Wine encontrado: {wine_version.stdout.strip()}")
        
        # Configura variáveis de ambiente do Wine
        os.environ["WINEDEBUG"] = "-all"
        os.environ["WINEDLLOVERRIDES"] = "mscoree,mshtml="
        
        # Verifica se o Python já está instalado no Wine
        python_check = subprocess.run(
            ["wine", "python", "--version"],
            capture_output=True,
            text=True
        )
        
        if python_check.returncode != 0:
            print("Python não encontrado no ambiente Wine. Instalando Python para Windows...")
            
            # Baixa o instalador do Python para Windows
            py_version = "3.10.11"  # Versão compatível com PyQt6
            py_installer = f"python-{py_version}-amd64.exe"
            py_url = f"https://www.python.org/ftp/python/{py_version}/{py_installer}"
            
            # Cria diretório temporário se não existir
            os.makedirs("temp", exist_ok=True)
            
            # Baixa o instalador do Python
            print(f"Baixando {py_url}...")
            subprocess.run(
                ["wget", "-O", f"temp/{py_installer}", py_url],
                check=True
            )
            
            # Instala o Python silenciosamente no Wine
            print("Instalando Python no Wine (isso pode demorar)...")
            subprocess.run(
                ["wine", f"temp/{py_installer}", "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"],
                check=True
            )
            
            print("Python instalado no ambiente Wine.")
        else:
            print(f"Python já instalado no Wine: {python_check.stdout.strip()}")
        
        # Instala dependências no Python do Wine
        print("Instalando dependências no Python do Wine...")
        subprocess.run(
            ["wine", "python", "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        
        # Instala PyInstaller e PyQt6 no Wine
        subprocess.run(
            ["wine", "python", "-m", "pip", "install", "pyinstaller", "PyQt6"],
            check=True
        )
        
        print("Ambiente Wine configurado com sucesso para compilação cross-platform")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"Erro na configuração do Wine: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False

# Função para compilar para Windows usando Wine
def build_windows_executable():
    """Compila o executável para Windows usando Wine"""
    if platform.system() != "Linux":
        print("Esta função deve ser executada apenas no Linux/WSL")
        return False
    
    # Configura o ambiente Wine se necessário
    if not setup_wine_environment():
        print("Falha na configuração do ambiente Wine")
        return False
    
    # Diretório de saída
    dist_dir = Path("dist-windows")
    dist_dir.mkdir(exist_ok=True)
    
    # Ícone
    icon_path = Path("resources/icons/simplerename.ico")
    if not icon_path.exists():
        print("Aviso: Ícone não encontrado")
        icon_param = ""
    else:
        icon_param = f"--icon={icon_path}"
    
    try:
        print("Compilando executável Windows com PyInstaller via Wine...")
        
        # Comando para PyInstaller no Wine
        cmd = [
            "wine", "python", "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--windowed",
            icon_param,
            "--name=SimpleRename",
            "--distpath=dist-windows",
            "--add-data=resources;resources",
            "--hidden-import=PyQt6",
            "--hidden-import=PyQt6.QtCore",
            "--hidden-import=PyQt6.QtGui",
            "--hidden-import=PyQt6.QtWidgets",
            "main.py"
        ]
        
        # Remove parâmetros vazios
        cmd = [c for c in cmd if c]
        
        # Executa o comando
        subprocess.run(cmd, check=True)
        
        # Verifica se o executável foi criado
        exe_path = dist_dir / "SimpleRename.exe"
        if exe_path.exists():
            print(f"Executável Windows criado com sucesso: {exe_path}")
            return True
        else:
            print(f"Compilação concluída, mas o executável não foi encontrado em {exe_path}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Erro ao compilar com PyInstaller no Wine: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False

# Função para criar o instalador NSIS
def create_nsis_installer():
    """Cria o instalador NSIS para Windows"""
    if platform.system() != "Linux":
        print("Esta função deve ser executada apenas no Linux/WSL")
        return False
    
    try:
        # Verifica se o NSIS está instalado
        nsis_check = subprocess.run(
            ["which", "makensis"],
            capture_output=True,
            text=True
        )
        
        if nsis_check.returncode != 0:
            print("NSIS não encontrado. Instale com: sudo apt install nsis")
            return False
        
        print(f"NSIS encontrado: {nsis_check.stdout.strip()}")
        
        # Verifica se o executável existe
        exe_path = Path("dist-windows/SimpleRename.exe")
        if not exe_path.exists():
            print(f"Executável não encontrado em {exe_path}")
            return False
        
        # Cria script NSIS
        nsis_script = """
; SimpleRename Installer Script
!define APPNAME "SimpleRename"
!define COMPANYNAME "simplerename"
!define DESCRIPTION "A lightweight file renaming tool"
!define VERSION "0.0.4"
!define INSTALLSIZE 20000

; Include Modern UI
!include "MUI2.nsh"

; General
Name "${APPNAME}"
OutFile "dist-windows/SimpleRenameSetup.exe"
InstallDir "$PROGRAMFILES64\\${APPNAME}"
InstallDirRegKey HKLM "Software\\${APPNAME}" "Install_Dir"

; Interface Configuration
!define MUI_ICON "resources/icons/simplerename.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_ABORTWARNING

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer sections
Section "Install"
    SetOutPath $INSTDIR
    
    ; Application files
    File "dist-windows\\SimpleRename.exe"
    
    ; Create Program Files directory structure
    CreateDirectory "$INSTDIR\\resources"
    CreateDirectory "$INSTDIR\\resources\\icons"
    
    ; Copy resources
    File /r "resources\\icons\\simplerename.ico" "$INSTDIR\\resources\\icons\\"
    
    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\\${APPNAME}"
    CreateShortcut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\SimpleRename.exe"
    CreateShortcut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\SimpleRename.exe"
    
    ; Write uninstaller information to registry
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayIcon" "$INSTDIR\\resources\\icons\\simplerename.ico"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "URLInfoAbout" "https://github.com/simplerename/simplerename"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "NoRepair" 1
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

; Uninstaller section
Section "Uninstall"
    ; Remove application files
    Delete "$INSTDIR\\SimpleRename.exe"
    Delete "$INSTDIR\\uninstall.exe"
    
    ; Remove resources
    RMDir /r "$INSTDIR\\resources"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk"
    Delete "$DESKTOP\\${APPNAME}.lnk"
    RMDir "$SMPROGRAMS\\${APPNAME}"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"
    DeleteRegKey HKLM "Software\\${APPNAME}"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
SectionEnd
"""
        
        # Salva o script NSIS
        with open("installer.nsi", "w") as f:
            f.write(nsis_script)
        
        # Executa o NSIS
        print("Criando instalador NSIS...")
        subprocess.run(["makensis", "installer.nsi"], check=True)
        
        # Verifica se o instalador foi criado
        installer_path = Path("dist-windows/SimpleRenameSetup.exe")
        if installer_path.exists():
            print(f"Instalador Windows criado com sucesso: {installer_path}")
            return True
        else:
            print(f"NSIS executado, mas instalador não encontrado em {installer_path}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Erro ao criar instalador NSIS: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False

setup(
    name="simplerename",
    version="0.0.4",
    description="A simple batch file renaming tool",
    author="simplerename",
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
    # Verifica se estamos no Linux/WSL e compilando para Windows
    if platform.system() == "Linux" and "--windows" in sys.argv:
        print("Iniciando compilação cross-platform para Windows a partir do WSL...")
        
        # Configuração e compilação Windows
        if build_windows_executable():
            print("Compilação para Windows concluída com sucesso!")
            
            # Cria instalador se solicitado
            if "--installer" in sys.argv:
                if create_nsis_installer():
                    print("Instalador Windows criado com sucesso!")
                else:
                    print("Falha ao criar o instalador Windows.")
        else:
            print("Falha na compilação para Windows.")
    else:
        # Comportamento padrão
        create_pyinstaller_spec()
