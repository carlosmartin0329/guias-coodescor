#!/usr/bin/env pwsh
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir
Write-Host "Iniciando Guias Coodescor..." -ForegroundColor Cyan
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 (Join-Path $scriptDir 'run_app.py')
    exit $LASTEXITCODE
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    python (Join-Path $scriptDir 'run_app.py')
    exit $LASTEXITCODE
}
Write-Host "No se encontro 'py' ni 'python' en este sistema." -ForegroundColor Yellow
Write-Host "Instale Python 3 desde: https://www.python.org/downloads/" -ForegroundColor Yellow
Write-Host "Despues, ejecute: `py -3 run_app.py` o este script nuevamente." -ForegroundColor Yellow
