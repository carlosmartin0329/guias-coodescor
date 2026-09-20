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
LAST_GIT_STATE = None
LAST_FILE_STATE = None


def get_git_state() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def snapshot_files() -> dict:
    snapshot = {}
    for folder, _, files in os.walk(ROOT):
        if ".git" in folder.split(os.sep):
            continue
        for filename in files:
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
    global LAST_GIT_STATE, LAST_FILE_STATE

    git_state = get_git_state()
    if LAST_GIT_STATE is not None and git_state != LAST_GIT_STATE:
        stop_service()
        start_service()
        LAST_GIT_STATE = git_state
        LAST_FILE_STATE = snapshot_files()
        return

    file_state = snapshot_files()
    if LAST_FILE_STATE is not None and file_state != LAST_FILE_STATE:
        stop_service()
        start_service()
        LAST_FILE_STATE = file_state
        LAST_GIT_STATE = git_state
        return

    LAST_GIT_STATE = git_state
    LAST_FILE_STATE = file_state


def main():
    print("[watcher] Monitoreando cambios del proyecto...")
    print(f"[watcher] Ruta: {ROOT}")
    print("[watcher] Se reiniciará automáticamente cuando detecte cambios en Git o archivos.")
    print("[watcher] Presiona Ctrl+C para detener.")

    start_service()
    LAST_GIT_STATE = get_git_state()
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
