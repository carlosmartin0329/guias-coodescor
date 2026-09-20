@echo off
pushd "%~dp0" || (echo No se pudo acceder a la carpeta del proyecto & pause & exit /b 1)
echo Iniciando Guías Coodescor...
REM Intenta el lanzador py (Python Launcher for Windows) primero
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
echo Luego ejecute este script de nuevo o abra PowerShell y ejecute `py -3 run_app.py`.
pause
popd
