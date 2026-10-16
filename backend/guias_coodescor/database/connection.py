#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestión de conexiones a la base de datos SQLite.
Incluye PRAGMAs recomendados y fábrica de conexiones seguras.
"""
import sqlite3
import threading
from contextlib import contextmanager

import guias_coodescor.config as _cfg

_LOCK = threading.Lock()
_SCHEMA_VERSION = 1


def get_connection(timeout: int = 20) -> sqlite3.Connection:
    """
    Devuelve una conexión a la base de datos con PRAGMAs recomendados.
    - WAL mode para concurrencia de lectores/escritores.
    - Foreign keys activadas.
    - Row factory para acceso por nombre de columna.

    Nota: lee DB_PATH dinámicamente desde el módulo config cada llamada para
    permitir sobrescritura en tests (BD temporal por run).
    """
    conn = sqlite3.connect(_cfg.DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    """
    Context manager para obtener un cursor y opcionalmente hacer commit.
    Cierra la conexión automáticamente.

    Uso:
        with db_cursor(commit=True) as cur:
            cur.execute(...)
    """
    conn = get_connection()
    try:
        yield conn.cursor()
        if commit:
            conn.commit()
    finally:
        conn.close()


@contextmanager
def db_connection(commit: bool = False):
    """
    Context manager para obtener una conexión y opcionalmente hacer commit.
    Útil cuando se necesita ejecutar varias consultas relacionadas.
    """
    conn = get_connection()
    try:
        yield conn
        if commit:
            conn.commit()
    finally:
        conn.close()


def get_db_lock() -> threading.Lock:
    """Devuelve el lock global para operaciones de escritura críticas."""
    return _LOCK


def get_receptores_connection(timeout: int = 20) -> sqlite3.Connection:
    """Conexión separada a la base temporal de receptores (datos PII).
    WAL mode + FK activados. No comparte archivo con guias.db para aislamiento.

    Nota: lee RECEPTORES_DB_PATH dinámicamente desde el módulo config cada
    llamada para permitir sobrescritura en tests (BD temporal por run).
    """
    conn = sqlite3.connect(_cfg.RECEPTORES_DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


@contextmanager
def receptores_db_connection(commit: bool = False):
    """Context manager para conexiones a la base de receptores."""
    conn = get_receptores_connection()
    try:
        yield conn
        if commit:
            conn.commit()
    finally:
        conn.close()
