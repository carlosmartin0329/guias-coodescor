#!/usr/bin/env pwsh
# Lanza el backend de Guias Coodescor (http://localhost:8000).
# Ubicacion: deploy/windows/run.ps1  ->  el backend esta en ../../backend
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir = Join-Path $scriptDir '..\..\backend' | Resolve-Path
Set-Location $backendDir
Write-Host "Iniciando Guias Coodescor..." -ForegroundColor Cyan
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 (Join-Path $backendDir 'run_app.py')
    exit $LASTEXITCODE
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    python (Join-Path $backendDir 'run_app.py')
    exit $LASTEXITCODE
}
Write-Host "No se encontro 'py' ni 'python' en este sistema." -ForegroundColor Yellow
Write-Host "Instale Python 3 desde: https://www.python.org/downloads/" -ForegroundColor Yellow
