@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH
    pause
    exit /b 1
)
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"
<<<<<<< HEAD
=======
set "COODESCOR_CAPTCHA_BYPASS_KEY=PROD-BYPASS-LOCAL-8721"
>>>>>>> 362aef51f3bc7584e3d225758f36d482900a0f28
echo ============================================
echo  GUIAS COODESCOR - Iniciando servidor...
echo  URL: http://localhost:8000
echo  Presiona Ctrl+C para detener
echo ============================================
:INICIAR
python run_app.py
if %ERRORLEVEL% neq 0 (
    echo [AVISO] Servidor cayo. Reiniciando en 3s...
    timeout /t 3 /nobreak >nul
    goto :INICIAR
)
pause
