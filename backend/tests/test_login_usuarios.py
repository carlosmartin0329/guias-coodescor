#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pruebas de login de los usuarios predeterminados del sistema.

Antes este archivo era un script suelto que ejecutaba ``sys.exit()`` al
importarse. Al vivir dentro de ``tests/`` y llamarse ``test_*.py``, pytest lo
importaba durante la recolección y la suite completa abortaba con
``INTERNALERROR ... SystemExit``. Ahora es un módulo de pytest normal:
``setup_module`` aísla una base de datos temporal y las pruebas solo afirman.

Uso:
    py -3 -m pytest tests/test_login_usuarios.py -v
"""
import os
import shutil
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_ROOT)
for _p in (_BACKEND, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import guias_coodescor.config as _config_mod

_TEMP_DIR = ""

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


def setup_module(module):
    """Crea una base de datos temporal propia de este módulo."""
    global _TEMP_DIR
    _TEMP_DIR = tempfile.mkdtemp(prefix="coodescor_login_test_")
    data = os.path.join(_TEMP_DIR, "data")
    os.makedirs(os.path.join(data, "adjuntos"), exist_ok=True)
    os.makedirs(os.path.join(data, "respaldos"), exist_ok=True)

    _config_mod.DATA_DIR = data
    _config_mod.ADJUNTOS_DIR = os.path.join(data, "adjuntos")
    _config_mod.BACKUP_DIR = os.path.join(data, "respaldos")
    _config_mod.DB_PATH = os.path.join(data, "guias.db")
    _config_mod.RECEPTORES_DB_PATH = os.path.join(data, "receptores.db")
    _config_mod.LOG_DIR = data
    _config_mod.LOG_FILE = os.path.join(data, "test_login.log")

    from guias_coodescor.database.models import init_db

    init_db()


def teardown_module(module):
    """Elimina el directorio temporal del módulo."""
    if _TEMP_DIR:
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)


@pytest.mark.parametrize("usuario,clave,rol_esperado", USUARIOS_PRUEBA)
def test_login_usuario_predeterminado(usuario, clave, rol_esperado):
    """Cada usuario semilla inicia sesión con su clave y rol correctos."""
    from guias_coodescor.services.auth_service import login

    sid, cookie, datos = login(
        usuario, clave, ip="127.0.0.1", user_agent="test-login/1.0"
    )

    assert sid, "login debe devolver un SID"
    assert cookie, "login debe devolver la cookie de sesión"
    assert datos.get("rol") == rol_esperado, (
        f"{usuario}: rol esperado={rol_esperado}, obtenido={datos.get('rol')}"
    )
    assert datos.get("activo"), f"{usuario}: la cuenta debe quedar activa"


def test_login_rechaza_clave_incorrecta():
    """Una clave incorrecta no debe crear sesión."""
    from guias_coodescor.services.auth_service import AuthError, login

    with pytest.raises(AuthError):
        login("admin", "clave-incorrecta", ip="127.0.0.1", user_agent="test-login/1.0")


def test_login_rechaza_usuario_inexistente():
    """Un usuario que no existe no debe revelar nada ni crear sesión."""
    from guias_coodescor.services.auth_service import AuthError, login

    with pytest.raises(AuthError):
        login("no-existe-xyz", "cualquiera", ip="127.0.0.1", user_agent="test-login/1.0")
