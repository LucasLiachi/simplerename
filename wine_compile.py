#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de compilação cross-platform para SimpleRename.
Este script compila a aplicação SimpleRename para Windows a partir do Linux (WSL)
"""

import os
import sys
import subprocess
import platform
import zipfile
import shutil
import time
from pathlib import Path

def setup_wine_environment():
    """Configura o ambiente Wine para compilação cross-platform"""
    try:
        # Verifica se o Wine está instalado
        wine_version = subprocess.run(
            ["wine", "--version"], 
            capture_output=True, 
            text=True
        )
        if (wine_version.returncode != 0):
            print("Wine não encontrado. Instale com: sudo apt install wine64")
            return False
        
        print(f"Wine encontrado: {wine_version.stdout.strip()}")
        
        # Configura variáveis de ambiente do Wine
        os.environ["WINEDEBUG"] = "-all"
        os.environ["WINEDLLOVERRIDES"] = "mscoree,mshtml="
        
        # Cria diretório temporário
        os.makedirs("temp", exist_ok=True)
        
        # Verifica se o Python portátil já existe
        portable_py_dir = Path("temp/python-embed")
        python_exe = portable_py_dir / "python.exe"
        pip_file = portable_py_dir / "get-pip.py"
        
        if not python_exe.exists():
            print("Python portátil não encontrado. Baixando Python embarcado (não requer instalação)...")
            
            # Abordagem com Python embarcado
            embed_url = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
            embed_file = "temp/python-embed.zip"
            
            print(f"Baixando {embed_url}...")
            subprocess.run(
                ["wget", "-O", embed_file, embed_url],
                check=True
            )
            
            # Extrair Python embarcado
            os.makedirs(portable_py_dir, exist_ok=True)
            
            print("Extraindo Python embarcado...")
            subprocess.run(
                ["7z", "x", embed_file, f"-o{portable_py_dir}"],
                check=True
            )
            
            print("Python embarcado extraído.")
            
            # Baixa e instala get-pip.py
            pip_url = "https://bootstrap.pypa.io/get-pip.py"
            
            print("Baixando get-pip.py...")
            subprocess.run(
                ["wget", "-O", str(pip_file), pip_url],
                check=True
            )
            
            # Modifica python310._pth para habilitar import site
            pth_file = portable_py_dir / "python310._pth"
            if pth_file.exists():
                print("Configurando Python embarcado para suportar pip...")
                with open(pth_file, 'r') as f:
                    content = f.read()
                
                # Descomenta a linha import site
                content = content.replace("#import site", "import site")
                
                with open(pth_file, 'w') as f:
                    f.write(content)
            
            print(f"Python portátil configurado em: {python_exe}")
        
        # Define o caminho do Python como variável de ambiente
        os.environ["WINE_PYTHON"] = str(python_exe)
        
        # Testa se o Python está funcionando
        try:
            print("Testando Python no Wine...")
            result = subprocess.run(
                ["wine", str(python_exe), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"Python encontrado no Wine: {result.stdout.strip()}")
            else:
                print(f"Erro ao executar Python no Wine: {result.stderr}")
                return False
        except Exception as e:
            print(f"Erro ao testar Python no Wine: {e}")
            return False
        
        # Instala dependências no Python do Wine
        print("Instalando dependências no Python portátil...")
        
        # Adicionamos o Scripts ao PATH
        scripts_dir = portable_py_dir / "Scripts"
        pip_exe = scripts_dir / "pip.exe"
        
        try:
            # Verifica se pip já está instalado
            if not pip_exe.exists():
                # Verifica se get-pip.py existe, caso contrário, baixa
                if not pip_file.exists():
                    print("Baixando get-pip.py...")
                    pip_url = "https://bootstrap.pypa.io/get-pip.py"
                    subprocess.run(
                        ["wget", "-O", str(pip_file), pip_url],
                        check=True
                    )
                
                # Instala pip
                print("Instalando pip...")
                subprocess.run(
                    ["wine", str(python_exe), str(pip_file)],
                    check=True
                )
            
            # Verifica novamente se pip foi instalado corretamente
            if not pip_exe.exists():
                print(f"Pip não foi instalado corretamente. Arquivo não encontrado: {pip_exe}")
                return False
            
            print("Atualizando pip...")
            subprocess.run(
                ["wine", str(pip_exe), "install", "--upgrade", "pip"],
                check=True
            )
            
            # Instala PyInstaller, PyQt6 e Pillow
            print("Instalando PyInstaller, PyQt6 e Pillow (isso pode demorar)...")
            subprocess.run(
                ["wine", str(pip_exe), "install", "pyinstaller", "PyQt6", "pillow"],
                check=True
            )
            
            print("Ambiente Wine configurado com sucesso para compilação cross-platform")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Erro ao instalar dependências: {e}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Erro na configuração do Wine: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False

def build_windows_executable():
    """Compila o executável para Windows usando Wine"""
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
        
        # Obtém o caminho do Python no ambiente Wine
        py_command = os.environ.get("WINE_PYTHON", "python")
        
        # Comando para PyInstaller no Wine
        cmd = [
            "wine", py_command, "-m", "PyInstaller",
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
        
        print(f"Executando comando: {' '.join(cmd)}")
        
        # Executa o comando
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Verifica se houve erro e tenta uma abordagem alternativa
        if result.returncode != 0:
            print("Erro na compilação com PyInstaller. Detalhes:")
            print(result.stderr)
            print("Tentando abordagem alternativa com spec file...")
            
            # Cria um arquivo .spec para o PyInstaller
            spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon_path}' if os.path.exists('{icon_path}') else None,
)
"""
            
            # Salva o arquivo .spec
            with open("SimpleRename_wine.spec", "w") as f:
                f.write(spec_content)
            
            # Tenta compilar usando o arquivo .spec
            alt_cmd = [
                "wine", py_command, "-m", "PyInstaller",
                "--clean",
                "--noconfirm",
                "SimpleRename_wine.spec",
                f"--distpath=dist-windows"
            ]
            
            print(f"Executando comando alternativo: {' '.join(alt_cmd)}")
            subprocess.run(alt_cmd, check=True)
        
        # Verifica se o executável foi criado
        exe_path = dist_dir / "SimpleRename.exe"
        if (exe_path.exists()):
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

def main():
    """Função principal"""
    print("=" * 50)
    print("SimpleRename - Compilação Cross-Platform para Windows")
    print("=" * 50)
    print()
    
    # Compila o executável Windows
    if build_windows_executable():
        print("Executável Windows compilado com sucesso!")
        print("\nCompilação finalizada com sucesso!")
        return True
    else:
        print("Falha ao compilar o executável Windows.")
        return False

if __name__ == "__main__":
    main()