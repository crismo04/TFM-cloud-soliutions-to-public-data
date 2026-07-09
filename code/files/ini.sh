#!/bin/bash
# iniciar.sh

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\e[36m=> Creando el entorno virtual '$VENV_DIR'...\e[0m"
    python3 -m venv $VENV_DIR
fi

echo -e "\e[36m=> Activando...\e[0m"
source $VENV_DIR/bin/activate

echo -e "\e[36m=> Dependencias...\e[0m"
pip install --upgrade pip
pip install -r code/files/requirements.txt -q

echo -e "\e[32m=> Descargando...\e[0m"
python code/files/01_descarga.py