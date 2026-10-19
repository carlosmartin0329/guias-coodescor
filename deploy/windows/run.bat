@echo off
REM Lanza el backend de Guias Coodescor (http://localhost:8000).
REM Ubicacion: deploy\windows\run.bat  ->  el backend esta en ..\..\backend
pushd "%~dp0..\..\backend" || (echo No se pudo acceder a la carpeta backend & pause & exit /b 1)
echo Iniciando Guias Coodescor...
REM Intenta primero el lanzador py (Python Launcher for Windows)
py -3 run_app.py
if %ERRORLEVEL%==0 (
  popd
  exit /b 0
)
REM Si falla, intenta python en PATH
python run_app.py
if %ERRORLEVEL%==0 (
  popd
  exit /b 0
)
echo.
echo No se encontro 'py' ni 'python' en el sistema.
echo Instale Python 3 desde https://www.python.org/downloads/ y active la casilla "Add Python to PATH".
echo Luego ejecute este script de nuevo.
pause
popd
