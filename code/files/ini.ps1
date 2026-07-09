# iniciar.ps1

$VENV_DIR = ".venv"

if (-not (Test-Path -Path $VENV_DIR)) {
    Write-Host "=> Creando el entorno virtual '$VENV_DIR'..." -ForegroundColor Cyan
    py -3.14 -m venv $VENV_DIR     # en este caso es la version 3.14, cambiar si no
}

Write-Host "=> Activando..." -ForegroundColor Cyan
. $VENV_DIR\Scripts\Activate.ps1

Write-Host "=> Dependencias..." -ForegroundColor Cyan
python -m pip install --upgrade pip -q
pip install -r code\files\requirements.txt

Write-Host "=> Descargando..." -ForegroundColor Green
python code\files\01_descarga.py