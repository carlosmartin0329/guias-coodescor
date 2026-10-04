#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 COODESCOR · Guías de Transporte Digitales  (Acta de Entrega de Mercancías)
----------------------------------------------------------------------------
 Punto de entrada único. Inicializa DB, logging y arranca el servidor HTTP.
 Sistema LOCAL, sin nube, sin licencias, sin dependencias externas:
   - Python 3 estándar (stdlib)  -> no requiere pip ni instalaciones
   - SQLite (viene con Python)   -> base de datos local
   - Navegador del celular/PC    -> interfaz (firma táctil, foto, QR opcional)

 Uso:   python app.py          y abrir  http://localhost:8000
        En la red local:       http://<IP-del-PC>:8000  desde los celulares
============================================================================
"""
import signal
import sys
import threading
import time
from http.server import ThreadingHTTPServer

import guias_coodescor.config as _cfg
from guias_coodescor.api.router import RequestHandler, get_host_port
from guias_coodescor.core.logging_config import configurar_logging, get_logger
from guias_coodescor.core.paths import preparar as _preparar_datos
from guias_coodescor.database.models import init_db
from guias_coodescor.services.receptores_service import purgar_receptores_vencidos

# Se resuelve la ubicación de datos antes de importar nada que la use en tiempo
# de import (config ya lo hace), para poder informar al usuario si hubo migración.
_preparado = getattr(_cfg, "_preparado", {}) or _preparar_datos()


def banner(host: str, port: int, data_dir: str = "") -> str:
    return "\n".join([
        "=" * 62,
        "  Guías Coodescor · sistema LOCAL iniciado",
        f"  En este equipo:   http://localhost:{port}",
        f"  En la red Wi-Fi:  http://<IP-de-este-PC>:{port}",
        f"  Datos:            {data_dir}" if data_dir else "",
        "  Usuarios iniciales: use las claves entregadas por Coodescor.",
        "  ⚠️  Cambie las claves iniciales desde Admin → Usuarios.",
        "  Pulsa Ctrl+C para detener.",
        "=" * 62,
    ])


def _instalar_signal_handler(srv: ThreadingHTTPServer, log):
    def _detener(signum, frame):
        log.info("Señal %s recibida. Deteniendo servidor...", signum)
        try:
            srv.shutdown()
        except Exception:
            pass
        print("\nDetenido.")
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _detener)
        signal.signal(signal.SIGTERM, _detener)
    except (ValueError, AttributeError):
        pass


def _arrancar_cron_purga_receptores(log):
    """
    Hilo daemon que ejecuta `purgar_receptores_vencidos()` cada 60 minutos
    (3600s). Primer ciclo corre 60s después del arranque (no inmediato) para
    no competir con el boot.
    """
    def _ciclo():
        try:
            time.sleep(60)
            while True:
                try:
                    purgar_receptores_vencidos()
                except Exception as ex:
                    log.warning("Cron purga receptores: error ignorado: %s", ex)
                time.sleep(3600)
        except Exception:
            return

    t = threading.Thread(target=_ciclo, name="receptores-purga-cron", daemon=True)
    t.start()
    log.info("Cron purga receptores temporales programado (cada 60 min, hilo daemon).")


def _preparar_consola() -> None:
    """
    Fuerza UTF-8 en la salida de consola.

    La consola de Windows usa cp1252 por defecto, y un carácter fuera de esa
    tabla (el aviso, una ruta con acentos) provoca UnicodeEncodeError y detiene
    el arranque. Con 'replace' el banner siempre se imprime.
    """
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main():
    _preparar_consola()
    configurar_logging()
    logger = get_logger("guias_coodescor.boot")

    from guias_coodescor.config import DATA_DIR, DATA_DIR_ORIGEN

    if _preparado.get("migracion"):
        logger.warning(_preparado["migracion"])
        print("\n[MIGRACIÓN] " + _preparado["migracion"] + "\n")

    try:
        init_db()
        logger.info("Base de datos inicializada correctamente")
    except Exception as ex:
        logger.exception("Fallo al inicializar la base de datos: %s", ex)
        print(f"Error al inicializar la base de datos: {ex}", file=sys.stderr)
        sys.exit(1)

    _arrancar_cron_purga_receptores(logger)

    host, port = get_host_port()
    try:
        srv = ThreadingHTTPServer((host, port), RequestHandler)
    except OSError as ex:
        logger.error("No se pudo abrir el puerto %s: %s", port, ex)
        print(
            f"ERROR: No se pudo abrir el puerto {port}. "
            f"Verifique que no esté en uso por otra aplicación.\nDetalle: {ex}",
            file=sys.stderr,
        )
        sys.exit(2)

    _instalar_signal_handler(srv, logger)

    print(banner(host, port, DATA_DIR))
    logger.info("Datos en %s (origen: %s)", DATA_DIR, DATA_DIR_ORIGEN)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")
    finally:
        try:
            srv.server_close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
