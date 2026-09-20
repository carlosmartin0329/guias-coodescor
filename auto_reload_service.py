#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Observa cambios en el repositorio y reinicia el servicio principal
cuando detecta nuevos cambios en archivos o en el estado de Git.

Uso:
    py auto_reload_service.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_SCRIPT = ROOT / "run_app.py"
PROCESS = None
LAST_FILE_STATE = None
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", "data", "uploads"}
WATCHED_SUFFIXES = {
    ".bat", ".css", ".gradle", ".html", ".java", ".js", ".json",
    ".md", ".properties", ".ps1", ".py", ".sql", ".xml",
}


def snapshot_files() -> dict:
    snapshot = {}
    for folder, _, files in os.walk(ROOT):
        relative_folder = Path(folder).relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in relative_folder.parts):
            continue
        for filename in files:
            if Path(filename).suffix.lower() not in WATCHED_SUFFIXES:
                continue
            full_path = os.path.join(folder, filename)
            try:
                rel = os.path.relpath(full_path, ROOT)
                snapshot[rel] = os.path.getmtime(full_path)
            except OSError:
                pass
    return snapshot


def start_service():
    global PROCESS
    if PROCESS is not None and PROCESS.poll() is None:
        return

    print(f"\n[watcher] Iniciando servicio... ({APP_SCRIPT})")
    PROCESS = subprocess.Popen(
        [sys.executable, str(APP_SCRIPT)],
        cwd=str(ROOT),
        stdout=sys.stdout,
        stderr=sys.stderr,
        shell=False,
    )
    print(f"[watcher] PID del servicio: {PROCESS.pid}")


def stop_service():
    global PROCESS
    if PROCESS is None or PROCESS.poll() is not None:
        return

    print("\n[watcher] Reiniciando servicio por cambio detectado...")
    try:
        if sys.platform == "win32":
            PROCESS.terminate()
        else:
            PROCESS.send_signal(signal.SIGINT)
    except Exception:
        pass

    try:
        PROCESS.wait(timeout=10)
    except subprocess.TimeoutExpired:
        PROCESS.kill()
        PROCESS.wait(timeout=10)

    PROCESS = None


def check_for_changes():
    global LAST_FILE_STATE

    file_state = snapshot_files()
    if LAST_FILE_STATE is not None and file_state != LAST_FILE_STATE:
        stop_service()
        start_service()
        LAST_FILE_STATE = file_state
        return

    LAST_FILE_STATE = file_state


def main():
    print("[watcher] Monitoreando cambios del proyecto...")
    print(f"[watcher] Ruta: {ROOT}")
    print("[watcher] Se reiniciará automáticamente cuando detecte cambios en archivos fuente.")
    print("[watcher] Presiona Ctrl+C para detener.")

    start_service()
    LAST_FILE_STATE = snapshot_files()

    try:
        while True:
            time.sleep(2)
            check_for_changes()
    except KeyboardInterrupt:
        print("\n[watcher] Deteniendo monitor...")
        stop_service()
        sys.exit(0)


if __name__ == "__main__":
    main()
