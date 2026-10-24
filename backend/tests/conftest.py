"""Configuración de pytest para la suite de Guías Coodescor.

Responsabilidades:
1. Hacer importable el paquete ``guias_coodescor`` (``backend/``).
2. Aislar la suite COMPLETA de los datos de producción: pytest importa los
   módulos de prueba durante la recolección, y algunos de ellos ejecutan
   ``init_db()`` a nivel de módulo. Si la configuración apuntara todavía a
   ``C:\\ProgramData\\Coodescor\\Guias`` en ese momento, la suite leería o
   crearía archivos contra la instalación real. Aquí se fija
   ``COODESCOR_DATA_DIR`` a un directorio temporal ANTES de importar el
   paquete, de modo que cualquier import (incluido el de ``config.py``)
   resuelva sus rutas dentro del temporal.
3. Inicializar el esquema una vez en una base temporal válida, para que los
   módulos que no crean su propia base (p. ej. ``test_api_guias``) encuentren
   una BD coherente.
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --- Aislamiento temprano: antes de importar guias_coodescor.config ----------
_SESSION_TEMP = tempfile.mkdtemp(prefix="coodescor_pytest_")
_SESSION_DATA = os.path.join(_SESSION_TEMP, "data")
for _sub in ("", "adjuntos", "respaldos"):
    os.makedirs(os.path.join(_SESSION_DATA, _sub), exist_ok=True)

# Se fuerza (no setdefault) para que una variable de entorno del equipo de
# desarrollo no pueda redirigir las pruebas a datos reales por accidente.
os.environ["COODESCOR_DATA_DIR"] = _SESSION_DATA

import guias_coodescor.config as _config_mod  # noqa: E402  (después del env)

_config_mod.DATA_DIR = _SESSION_DATA
_config_mod.ADJUNTOS_DIR = os.path.join(_SESSION_DATA, "adjuntos")
_config_mod.BACKUP_DIR = os.path.join(_SESSION_DATA, "respaldos")
_config_mod.DB_PATH = os.path.join(_SESSION_DATA, "guias.db")
_config_mod.RECEPTORES_DB_PATH = os.path.join(_SESSION_DATA, "receptores.db")
_config_mod.LOG_DIR = _SESSION_DATA
_config_mod.LOG_FILE = os.path.join(_SESSION_DATA, "guias_coodescor.log")

from guias_coodescor.database.models import init_db  # noqa: E402

init_db()


def pytest_sessionfinish(session, exitstatus):
    """Borra el directorio temporal de la sesión (best-effort)."""
    import shutil

    shutil.rmtree(_SESSION_TEMP, ignore_errors=True)
