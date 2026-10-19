#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test corto: verifica login de cada usuario predeterminado del sistema.
Crea una BD temporal, inicializa el esquema y valida que cada usuario
de DEFAULT_USERS pueda autenticarse con su contraseña registrada.

Uso:
    py test_login_usuarios.py
"""
import os
import sys
import tempfile

# --- Arreglar rutas para importar el paquete --------------------------------
_ROOT = os.path.dirname(os.path.abspath(__file__))          # tests/
_BACKEND = os.path.dirname(_ROOT)                            # backend/
for _p in (_BACKEND, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# --- Configurar BD temporal -------------------------------------------------
import guias_coodescor.config as _config_mod
_TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_login_test_")
_TEMP_DATA = os.path.join(_TEMP_DIR, "data")
os.makedirs(_TEMP_DATA, exist_ok=True)
_config_mod.DATA_DIR = _TEMP_DATA
_config_mod.ADJUNTOS_DIR = os.path.join(_TEMP_DATA, "adjuntos")
_config_mod.DB_PATH = os.path.join(_TEMP_DATA, "guias.db")
_config_mod.RECEPTORES_DB_PATH = os.path.join(_TEMP_DATA, "receptores.db")
_config_mod.BACKUP_DIR = os.path.join(_TEMP_DATA, "respaldos")
_config_mod.LOG_DIR = _TEMP_DATA
_config_mod.LOG_FILE = os.path.join(_TEMP_DATA, "test_login.log")

os.makedirs(_config_mod.ADJUNTOS_DIR, exist_ok=True)
os.makedirs(_config_mod.BACKUP_DIR, exist_ok=True)

from guias_coodescor.database.models import init_db
from guias_coodescor.services.auth_service import login, AuthError
from guias_coodescor.config import DEFAULT_USERS

init_db()

# --- Usuarios a probar (usuario, contraseña, rol esperado) ------------------
USUARIOS_PRUEBA = [
    ("admin", "admin123", "admin"),
    ("administrativo", "adminbod123", "administrativo"),
    ("ventas", "ventas123", "ventas"),
    ("ventas2", "ventas123", "ventas"),
    ("ventas3", "ventas123", "ventas"),
    ("ventas4", "ventas123", "ventas"),
    ("ventas5", "ventas123", "ventas"),
    ("cedis", "cedis123", "cedis"),
    ("cedis2", "cedis123", "cedis"),
    ("transportador", "transpor123", "transportador"),
    ("transportador2", "transpor123", "transportador"),
    ("transportador3", "transpor123", "transportador"),
]

print("=" * 60)
print("TEST DE LOGIN - Usuarios del sistema Guías Coodescor")
print("=" * 60)

fallos = 0
exitos = 0

for usuario, clave, rol_esperado in USUARIOS_PRUEBA:
    try:
        sid, cookie, datos = login(usuario, clave, ip="127.0.0.1", user_agent="test-login/1.0")
        rol_real = datos.get("rol")
        activo = datos.get("activo")
        if rol_real != rol_esperado:
            print(f"  [ROL INCORRECTO] {usuario}: esperado={rol_esperado}, obtenido={rol_real}")
            fallos += 1
        elif not activo:
            print(f"  [INACTIVO] {usuario}: cuenta desactivada")
            fallos += 1
        else:
            print(f"  [OK] {usuario}  rol={rol_real}  sid={sid[:8]}...")
            exitos += 1
    except AuthError as ex:
        print(f"  [FALLO] {usuario}: {ex}")
        fallos += 1
    except Exception as ex:
        print(f"  [ERROR] {usuario}: {type(ex).__name__}: {ex}")
        fallos += 1

print("-" * 60)
print(f"Resultado: {exitos} exitosos, {fallos} fallidos de {len(USUARIOS_PRUEBA)} usuarios")
print("=" * 60)

if fallos > 0:
    sys.exit(1)
else:
    print("Todos los usuarios pueden iniciar sesión correctamente.")
    sys.exit(0)
