@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
REM Ubicacion: deploy\windows\iniciar_servidor.bat
REM Arranca el backend y lo reinicia automaticamente si se cae.
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"
REM La interfaz nueva (React) se sirve desde el backend. Si el build no existe,
REM se compila una vez antes de arrancar (evita que 8000 muestre la UI vieja).
if not exist "%ROOT%\frontend\dist\index.html" (
    echo [INFO] Compilando interfaz nueva...
    pushd "%ROOT%\frontend"
    call npm install
    call npm run build
    popd
)
cd /d "%ROOT%\backend"
REM Consistente con run.bat: prioriza el lanzador 'py -3'.
set "PYTHON=py -3"
py -3 --version >nul 2>&1
if errorlevel 1 set "PYTHON=python"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instale Python 3 y active "Add Python to PATH".
    pause
    exit /b 1
)
REM Entorno virtual: en la raiz del proyecto o dentro de backend
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
REM Configuracion opcional de Google Apps Script (confirmacion gratuita).
REM Copia backend\configuracion_google.env.example a configuracion_google.env
REM y completa los valores. No se versiona el archivo real.
if exist "%ROOT%\backend\configuracion_google.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\backend\configuracion_google.env") do (
        set "%%A=%%B"
    )
    echo [INFO] Configuracion de Google Apps Script cargada.
)
REM El bypass del CAPTCHA (COODESCOR_CAPTCHA_BYPASS_KEY) NO se define aqui:
REM no debe quedar una clave escrita en un script versionado. Si lo necesitas
REM solo para pruebas locales, defínela en tu sesion antes de ejecutar este script.
echo ============================================
echo  GUIAS COODESCOR - Iniciando servidor...
echo  URL: http://localhost:8000
echo  Presiona Ctrl+C para detener
echo ============================================
:INICIAR
%PYTHON% run_app.py
if %ERRORLEVEL% neq 0 (
    echo [AVISO] Servidor cayo. Reiniciando en 3s...
    timeout /t 3 /nobreak >nul
    goto :INICIAR
)
pause
