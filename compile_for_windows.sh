#!/bin/bash
# Script para compilação do SimpleRename para Windows a partir do WSL

# Cores para saída
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  SimpleRename - Compilação Cross-Platform ${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Verifica dependências
echo -e "${YELLOW}Verificando dependências necessárias...${NC}"

# Verifica Wine
if ! command -v wine &> /dev/null; then
    echo -e "${RED}Wine não encontrado. Instalando...${NC}"
    sudo apt-get update
    sudo apt-get install -y wine64
    if [ $? -ne 0 ]; then
        echo -e "${RED}Falha ao instalar Wine. Abortando.${NC}"
        exit 1
    fi
fi

# Verifica NSIS
if ! command -v makensis &> /dev/null; then
    echo -e "${RED}NSIS não encontrado. Instalando...${NC}"
    sudo apt-get update
    sudo apt-get install -y nsis
    if [ $? -ne 0 ]; then
        echo -e "${RED}Falha ao instalar NSIS. Abortando.${NC}"
        exit 1
    fi
fi

# Verifica wget
if ! command -v wget &> /dev/null; then
    echo -e "${RED}wget não encontrado. Instalando...${NC}"
    sudo apt-get update
    sudo apt-get install -y wget
    if [ $? -ne 0 ]; then
        echo -e "${RED}Falha ao instalar wget. Abortando.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Todas as dependências estão instaladas.${NC}"
echo ""

# Cria ambiente virtual Python se não existir
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Criando ambiente virtual Python...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Falha ao criar ambiente virtual. Verifique se python3-venv está instalado.${NC}"
        exit 1
    fi
fi

# Ativa ambiente virtual
echo -e "${YELLOW}Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Instala dependências Python
echo -e "${YELLOW}Instalando dependências Python...${NC}"
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}Falha ao instalar dependências Python. Abortando.${NC}"
    exit 1
fi

# Pergunta se quer criar o instalador
create_installer=0
read -p "Deseja criar o instalador também? (s/n): " yn
case $yn in
    [Ss]* ) create_installer=1;;
    * ) echo "Compilando apenas o executável.";;
esac

# Executa a compilação
echo -e "${YELLOW}Iniciando compilação cross-platform...${NC}"
echo ""

if [ $create_installer -eq 1 ]; then
    python setup.py --windows --installer
else
    python setup.py --windows
fi

# Verifica se o executável foi criado
if [ -f "dist-windows/SimpleRename.exe" ]; then
    echo -e "${GREEN}Executável criado com sucesso em dist-windows/SimpleRename.exe${NC}"
    
    # Verifica se o instalador foi criado
    if [ $create_installer -eq 1 ] && [ -f "dist-windows/SimpleRenameSetup.exe" ]; then
        echo -e "${GREEN}Instalador criado com sucesso em dist-windows/SimpleRenameSetup.exe${NC}"
    fi
    
    # Tenta mostrar como acessar os arquivos no Windows se estiver no WSL
    if command -v wslpath &> /dev/null; then
        windows_path=$(wslpath -w "$(pwd)/dist-windows")
        echo ""
        echo -e "${BLUE}Para acessar os arquivos compilados no Windows:${NC}"
        echo -e "1. Abra o Windows Explorer"
        echo -e "2. Navegue até: ${YELLOW}$windows_path${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Compilação concluída com sucesso!${NC}"
    exit 0
else
    echo -e "${RED}Falha na compilação. Verifique os erros acima.${NC}"
    exit 1
fi