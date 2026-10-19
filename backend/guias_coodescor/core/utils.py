#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilidades generales: fechas, hashing auxiliar (funciones puras sin dependencias),
validación de tipos de archivos, sanitización de paths y helpers comunes.
"""
import base64
import hashlib
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

import guias_coodescor.config as _cfg

_PASSWORD_HASH_ITERATIONS = 120_000


def normalizar_nit(nit: Optional[str]) -> str:
    """Normaliza NIT a solo digitos (sin puntos, guiones, espacios, leading zeros).

    Ejemplos:
      "800.000.000-1" -> "8000000001"
      " 900100100-7 " -> "9001001007"
      "NIT"        -> ""
    """
    if not nit:
        return ""
    digitos = re.sub(r"[^0-9]", "", str(nit))
    return digitos.lstrip("0")

_SALT_BYTE_LENGTH = 8


def hash_password_puro(clave: str, sal: str | None = None):
    """
    Genera el hash PBKDF2-HMAC-SHA256 de una contraseña (función pura, sin BD).
    Devuelve (hash_hex, sal_hex). No usar directamente para login; usar
    core.security.hash_password que aplica configuración centralizada.
    """
    if not clave:
        raise ValueError("Contraseña vacía")
    sal = sal or secrets.token_hex(_SALT_BYTE_LENGTH)
    h = hashlib.pbkdf2_hmac(
        "sha256",
        clave.encode("utf-8"),
        bytes.fromhex(sal),
        _PASSWORD_HASH_ITERATIONS,
    ).hex()
    return h, sal


def verificar_password_puro(clave_intento: str, pass_hash: str, sal: str) -> bool:
    """
    Verifica una contraseña contra su hash (función pura).
    Comparación en tiempo constante para evitar ataques de timing.
    """
    if not clave_intento or not pass_hash or not sal:
        return False
    try:
        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            clave_intento.encode("utf-8"),
            bytes.fromhex(sal),
            _PASSWORD_HASH_ITERATIONS,
        ).hex()
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(calculado, pass_hash)


def ahora_txt() -> str:
    """Devuelve la fecha/hora actual en formato ISO compacto (compatible con SQLite)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sumar_segundos(fecha_txt: str, segundos: int) -> str:
    """Suma segundos a una fecha en formato '%Y-%m-%d %H:%M:%S'."""
    dt = datetime.strptime(fecha_txt, "%Y-%m-%d %H:%M:%S") + timedelta(seconds=segundos)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fecha_expira_sesion(segundos: int) -> str:
    """Devuelve la fecha de expiración de una sesión a partir de ahora."""
    return sumar_segundos(ahora_txt(), segundos)


def fecha_pasada(fecha_txt: str) -> bool:
    """Indica si una fecha en formato texto ya pasó."""
    try:
        return datetime.strptime(fecha_txt, "%Y-%m-%d %H:%M:%S") < datetime.now()
    except (ValueError, TypeError):
        return True


def codigo_verificacion(guia_id: int, consecutivo: int) -> str:
    """
    Genera un código de verificación único y opaco para una guía.
    Útil para trazabilidad y verificación externa.
    """
    h = hashlib.sha256(f"{guia_id}-{consecutivo}".encode()).hexdigest()[:4].upper()
    return f"CD-{consecutivo}-{h}"


def extraer_extension_data_url(data_url: str) -> str:
    """
    Dado un data URL (data:image/png;base64,...), devuelve la extensión ('png' o 'jpg').
    Si no es reconocido devuelve 'bin'.
    """
    if not data_url or not data_url.startswith("data:image"):
        return "bin"
    cabecera = data_url[:30].lower()
    if "png" in cabecera:
        return "png"
    if "jpeg" in cabecera or "jpg" in cabecera:
        return "jpg"
    if "gif" in cabecera:
        return "gif"
    return "bin"


def data_url_a_bytes(data_url: str):
    """Extrae los bytes del payload base64 de un data URL. Devuelve None si no es válido."""
    if not data_url or "," not in data_url:
        return None
    try:
        _, payload = data_url.split(",", 1)
        return base64.b64decode(payload)
    except (ValueError, Exception):
        return None


def guardar_adjunto_bytes(nombre_archivo: str, datos: bytes) -> str:
    """
    Guarda bytes de un adjunto en la carpeta ADJUNTOS_DIR.
    Devuelve la ruta relativa tipo 'adjuntos/nombre.png'.
    Valida que el nombre no escape del directorio.
    """
    nombre_limpio = os.path.basename(nombre_archivo)
    ext = nombre_limpio.rsplit(".", 1)[-1].lower() if "." in nombre_limpio else ""
    if ext and ext not in _cfg.ALLOWED_IMAGE_EXT:
        raise ValueError(f"Extensión no permitida: {ext}")
    if len(datos) > _cfg.MAX_ADJUNTO_SIZE:
        raise ValueError("El adjunto excede el tamaño máximo permitido")
    ruta_abs = os.path.normpath(os.path.join(_cfg.ADJUNTOS_DIR, nombre_limpio))
    if os.path.commonpath([ruta_abs, os.path.normpath(_cfg.ADJUNTOS_DIR)]) != os.path.normpath(
        _cfg.ADJUNTOS_DIR
    ):
        raise ValueError("Ruta inválida para adjunto")
    with open(ruta_abs, "wb") as fh:
        fh.write(datos)
    return f"adjuntos/{nombre_limpio}"


def ruta_adjunto_segura(rel: str) -> str:
    """
    Resuelve la ruta de un adjunto para poder servirlo por HTTP.

    Solo admite imágenes dentro de ADJUNTOS_DIR. Es deliberado: DATA_DIR
    contiene la base de datos y los logs, así que resolver adjuntos contra
    DATA_DIR permitiría descargarlos. Acepta 'nombre.png' o el legacy
    'adjuntos/nombre.png' que se guardaba en la base de datos.
    """
    if not rel:
        raise ValueError("Ruta vacía")
    limpio = str(rel).replace("\\", "/").strip()
    # Sin separadores: solo el nombre final del archivo.
    if "/" in limpio:
        partes = [p for p in limpio.split("/") if p and p != "."]
        if partes and partes[0] == "adjuntos":
            partes = partes[1:]
        if len(partes) != 1:
            raise ValueError("Ruta de adjunto no permitida")
        limpio = partes[0]
    if not limpio or limpio.startswith("."):
        raise ValueError("Ruta de adjunto no permitida")

    ext = limpio.rsplit(".", 1)[-1].lower() if "." in limpio else ""
    if ext not in _cfg.ALLOWED_IMAGE_EXT:
        raise ValueError("Tipo de archivo no permitido para servir")

    base = os.path.normpath(_cfg.ADJUNTOS_DIR)
    ruta_abs = os.path.normpath(os.path.join(base, limpio))
    if os.path.commonpath([ruta_abs, base]) != base:
        raise ValueError("Ruta fuera del directorio permitido")
    if not os.path.isfile(ruta_abs):
        raise ValueError("Archivo no encontrado")
    return ruta_abs


def mime_por_extension(ext: str) -> str:
    """Devuelve el MIME type asociado a una extensión."""
    ext = ext.lower().lstrip(".")
    if ext in ("png",):
        return "image/png"
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "gif":
        return "image/gif"
    if ext == "svg":
        return "image/svg+xml"
    if ext in ("webp",):
        return "image/webp"
    if ext == "ico":
        return "image/x-icon"
    if ext == "css":
        return "text/css; charset=utf-8"
    if ext in ("js", "mjs"):
        return "text/javascript; charset=utf-8"
    if ext == "webmanifest":
        return "application/manifest+json"
    if ext == "html":
        return "text/html; charset=utf-8"
    if ext == "txt":
        return "text/plain; charset=utf-8"
    if ext == "pdf":
        return "application/pdf"
    return "application/octet-stream"


_NOMBRE_USUARIO_RE = re.compile(r"^[A-Za-z0-9_.@-]{3,50}$")


def validar_nombre_usuario(usuario: str) -> bool:
    """Valida formato de nombre de usuario."""
    return bool(usuario and _NOMBRE_USUARIO_RE.match(usuario))


def validar_rol(rol: str) -> bool:
    from guias_coodescor.config import ROLES_VALIDOS
    return rol in ROLES_VALIDOS


def ahora_milis() -> int:
    return int(time.time() * 1000)
