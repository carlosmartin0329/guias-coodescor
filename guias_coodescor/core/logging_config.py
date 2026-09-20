#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada de logging (stdlib-only).
Usa RotatingFileHandler para no crecer indefinidamente y imprime también a consola.
"""
import logging
from logging.handlers import RotatingFileHandler

from guias_coodescor.config import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)

_LOG_CONFIGURADO = False
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configurar_logging() -> logging.Logger:
    """Configura el logging raíz y devuelve el logger principal."""
    global _LOG_CONFIGURADO
    logger = logging.getLogger("guias_coodescor")
    if _LOG_CONFIGURADO:
        return logger
    nivel = getattr(logging, str(LOG_LEVEL).upper(), logging.INFO)
    logger.setLevel(nivel)
    fmt = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    consola = logging.StreamHandler()
    consola.setLevel(nivel)
    consola.setFormatter(fmt)
    logger.addHandler(consola)

    try:
        archivo = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        archivo.setLevel(nivel)
        archivo.setFormatter(fmt)
        logger.addHandler(archivo)
    except (OSError, PermissionError):
        logger.warning("No se pudo crear el archivo de log en %s", LOG_FILE)

    logger.propagate = False
    _LOG_CONFIGURADO = True
    return logger


def get_logger(nombre: str = "guias_coodescor") -> logging.Logger:
    return logging.getLogger(nombre)
