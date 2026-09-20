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
from http.server import ThreadingHTTPServer

from guias_coodescor.api.router import RequestHandler, get_host_port
from guias_coodescor.core.logging_config import configurar_logging, get_logger
from guias_coodescor.database.models import init_db


def banner(host: str, port: int) -> str:
    return "\n".join([
        "=" * 62,
        "  Guías Coodescor · sistema LOCAL iniciado",
        f"  En este equipo:   http://localhost:{port}",
        f"  En la red Wi-Fi:  http://<IP-de-este-PC>:{port}",
        "  Usuarios iniciales: admin/admin123 · ventas/ventas123 · cedis/cedis123",
        "  ⚠️  CAMBIE LAS CONTRASEÑAS POR DEFECTO desde el panel Admin.",
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


def main():
    configurar_logging()
    logger = get_logger("guias_coodescor.boot")

    try:
        init_db()
        logger.info("Base de datos inicializada correctamente")
    except Exception as ex:
        logger.exception("Fallo al inicializar la base de datos: %s", ex)
        print(f"Error al inicializar la base de datos: {ex}", file=sys.stderr)
        sys.exit(1)

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

    print(banner(host, port))
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
