#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lanzamiento desde la carpeta raíz del proyecto.
Asegura que se pueda importar 'guias_coodescor' como paquete y
arranca el servidor HTTP.

ENDURECIMIENTO (V2):
- Bucle de reinicio automático si serve_forever() retorna o lanza excepción.
- Backoff exponencial para no saturar si hay un crash loop permanente.
- Toda excepción del hilo principal se registra (traceback) en logger raíz
  antes de dormir y reintentar.
"""
import os
import sys
import time
import traceback

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from guias_coodescor.app import main

if __name__ == "__main__":
    MAX_BACKOFF = 60
    backoff = 1
    intentos = 0
    while True:
        intentos += 1
        try:
            main()
        except KeyboardInterrupt:
            print("\nDetenido por el usuario (Ctrl+C).")
            break
        except SystemExit as se:
            if se.code == 0:
                break
            print(f"[run_app] SystemExit code={se.code}. Reintentando en {backoff}s ...",
                  file=sys.stderr)
            time.sleep(backoff)
        except Exception as ex:
            print(
                f"[run_app] EXCEPCIÓN NO MANEJADA intento={intentos}: {type(ex).__name__}: {ex}",
                file=sys.stderr,
            )
            try:
                traceback.print_exc(file=sys.stderr)
            except Exception:
                pass
            print(f"[run_app] Reintentando en {backoff}s ...", file=sys.stderr)
            time.sleep(backoff)
        else:
            print(f"[run_app] serve_forever retornó sin excepción. "
                  f"Reintentando en {backoff}s ...", file=sys.stderr)
            time.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF)
