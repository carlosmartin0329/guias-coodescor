@echo off
chcp 65001 >nul
title Guías Coodescor - Servidor + ngrok (acceso público)

cd /d "%~dp0"

echo.
echo ============================================
echo   GUIAS COODESCOR - Servidor + ngrok
echo ============================================
echo.

REM 1. Verificar ngrok.exe
if not exist "ngrok.exe" (
    echo [ERROR] No se encontro ngrok.exe en %CD%
    pause
    exit /b 1
)

REM 2. Verificar configuracion de ngrok
ngrok.exe config check >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ngrok no tiene authtoken configurado.
    echo.
    echo Ejecuta primero:
    echo   ngrok.exe config add-authtoken TU_TOKEN
    echo.
    echo Obten tu token en: https://dashboard.ngrok.com/
    pause
    exit /b 1
)
echo [OK] ngrok configurado

REM 3. Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH
    pause
    exit /b 1
)

REM 4. Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

<<<<<<< HEAD
REM 5. Variables de entorno
REM El bypass del CAPTCHA (COODESCOR_CAPTCHA_BYPASS_KEY) queda DESACTIVADO a
REM proposito: expone el login a credential stuffing automatizado. Exponer este
REM sistema en internet exige HTTPS y credenciales propias ya cambiadas.
echo [OK] Bypass CAPTCHA inactivo (correcto para produccion)
=======
REM 5. Variables de entorno QA
set "COODESCOR_CAPTCHA_BYPASS_KEY=PROD-BYPASS-LOCAL-8721"
echo [OK] Bypass CAPTCHA activo para QA
>>>>>>> 362aef51f3bc7584e3d225758f36d482900a0f28

REM 6. Liberar puertos 8000 y 4040 si estan ocupados
for %%p in (8000 4040) do (
    netstat -ano | findstr ":%%p" | findstr "LISTENING" >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] Liberando puerto %%p...
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p" ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
        )
    )
)

REM 7. Iniciar servidor en background (nueva ventana)
echo.
echo [INFO] Iniciando servidor local en http://localhost:8000...
start "Servidor Guías Coodescor" /min cmd /c "python run_app.py"

REM 8. Esperar a que el servidor arranque
timeout /t 5 /nobreak >nul

REM 9. Verificar que el servidor respondio
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/login', timeout=10)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] El servidor local no respondio. Revisa la ventana del servidor.
    pause
    exit /b 1
)
echo [OK] Servidor local activo

REM 10. Iniciar ngrok en background (nueva ventana)
echo.
echo [INFO] Iniciando ngrok...
echo [INFO] Busca la URL publica en la ventana de ngrok o en http://localhost:4040
echo.
start "ngrok - Guías Coodescor" cmd /c "ngrok.exe http 8000 -log=stdout -log-format=logfmt"

REM 11. Esperar a que ngrok arranque
timeout /t 4 /nobreak >nul

REM 12. Obtener la URL publica desde la API de ngrok
echo.
echo ============================================
echo   OBTENIENDO URL PUBLICA...
echo ============================================
python -c "import urllib.request, json; r=urllib.request.urlopen('http://localhost:4040/api/tunnels', timeout=5); d=json.loads(r.read()); tuns=d.get('tunnels',[]); [print('  URL PUBLICA:', t['public_url']) for t in tuns if t.get('proto')=='https'] or [print('  URL PUBLICA:', t['public_url']) for t in tuns if t.get('proto')=='http']"

echo.
echo ============================================
echo   SERVIDOR ACTIVO
echo ============================================
echo   Local:  http://localhost:8000
echo   ngrok:  http://localhost:4040  (panel de ngrok)
echo.
echo   Detener todo:
echo     1. Cierra esta ventana
echo     2. Cierra las ventanas "Servidor" y "ngrok"
echo ============================================
echo.
pause
