# Ejecutar exportación a Supabase una sola vez
# Requiere: .env configurado con SUPABASE_URL y SUPABASE_KEY

cd /d "%~dp0"
if exist ".env" (
    for /f "usebackq delims=" %%a in (".env") do set "%%a"
)
py exportar_a_supabase.py

pause
