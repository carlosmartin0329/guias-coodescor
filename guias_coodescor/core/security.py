#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de seguridad:
- Hash y verificación de contraseñas (PBKDF2-HMAC-SHA256) via funciones puras en utils.
- Generación y validación de sesiones con expiración.
- Rate limiting por IP/usuario para login.
- Tokens CSRF básicos.
"""
import secrets
import threading
from typing import Dict, Optional, Tuple

from guias_coodescor.config import (
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    PASSWORD_MIN_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_DURATION_SECONDS,
    SID_BYTE_LENGTH,
)
from guias_coodescor.core.utils import (
    ahora_txt,
    fecha_expira_sesion,
    fecha_pasada,
    hash_password_puro,
    verificar_password_puro,
)
from guias_coodescor.database.connection import db_connection
from guias_coodescor.database.models import limpiar_sesiones_expiradas


_rate_lock = threading.Lock()
_intentos_login: Dict[str, Dict] = {}


def hash_password(clave: str, sal: Optional[str] = None) -> Tuple[str, str]:
    """
    Genera el hash PBKDF2 de una contraseña.
    Devuelve (hash_hex, sal_hex). Wrapper sobre la función pura en utils.
    """
    return hash_password_puro(clave, sal)


def verificar_password(clave_intento: str, pass_hash: str, sal: str) -> bool:
    """Verifica una contraseña contra un hash almacenado en tiempo constante."""
    return verificar_password_puro(clave_intento, pass_hash, sal)


def validar_password_fuerte(clave: str) -> Optional[str]:
    """
    Valida que la contraseña cumpla requisitos mínimos.
    Devuelve None si es válida, o un mensaje de error si no.
    """
    if not clave:
        return "La contraseña no puede estar vacía"
    if len(clave) < PASSWORD_MIN_LENGTH:
        return f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres"
    return None


def generar_sid() -> str:
    """Genera un identificador de sesión criptográficamente seguro."""
    return secrets.token_hex(SID_BYTE_LENGTH)


def crear_sesion(
    usuario_id: int,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Crea una nueva sesión en BD y devuelve el sid."""
    sid = generar_sid()
    ahora = ahora_txt()
    expira = fecha_expira_sesion(SESSION_DURATION_SECONDS)
    with db_connection(commit=True) as conn:
        conn.execute(
            """
            INSERT INTO sesiones(sid, usuario_id, creada, expira, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sid, usuario_id, ahora, expira, ip, user_agent),
        )
        conn.execute(
            "UPDATE usuarios SET ultima_sesion = ?, intentos_fallidos = 0, bloqueado_hasta = NULL "
            "WHERE id = ?",
            (ahora, usuario_id),
        )
    return sid


def validar_sesion(sid: str) -> Optional[dict]:
    """
    Dado un sid, devuelve el dict del usuario activo asociado o None si la
    sesión no existe, expiró o el usuario está inactivo/bloqueado.
    Limpia sesiones expiradas de manera ocasional.
    """
    if not sid:
        return None
    if secrets.randbelow(50) == 0:
        try:
            limpiar_sesiones_expiradas()
        except Exception:
            pass
    with db_connection() as conn:
        fila = conn.execute(
            """
            SELECT s.sid, s.expira, u.*
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.sid = ? AND u.activo = 1
            """,
            (sid,),
        ).fetchone()
        if not fila:
            return None
        if fecha_pasada(fila["expira"]):
            conn.execute("DELETE FROM sesiones WHERE sid = ?", (sid,))
            conn.commit()
            return None
        if fila["bloqueado_hasta"] and not fecha_pasada(fila["bloqueado_hasta"]):
            return None
        return dict(fila)


def borrar_sesion(sid: str) -> None:
    if not sid:
        return
    with db_connection(commit=True) as conn:
        conn.execute("DELETE FROM sesiones WHERE sid = ?", (sid,))


def parsear_cookie_sid(cookie_header: Optional[str]) -> str:
    """Extrae el sid de la cabecera Cookie."""
    if not cookie_header:
        return ""
    for trozo in cookie_header.split(";"):
        trozo = trozo.strip()
        if trozo.startswith(SESSION_COOKIE_NAME + "="):
            return trozo[len(SESSION_COOKIE_NAME) + 1:]
    return ""


def cookie_set_sid(sid: str, http_only: bool = True, same_site: str = "Lax", secure: bool = False) -> str:
    """Construye la cabecera Set-Cookie para una sesión."""
    partes = [f"{SESSION_COOKIE_NAME}={sid}", "Path=/"]
    if http_only:
        partes.append("HttpOnly")
    if same_site:
        partes.append(f"SameSite={same_site}")
    if secure:
        partes.append("Secure")
    partes.append(f"Max-Age={SESSION_DURATION_SECONDS}")
    return "; ".join(partes)


def cookie_unset_sid() -> str:
    return f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0"


def _clave_bloqueo(ip: Optional[str], usuario: Optional[str]) -> str:
    return f"{ip or '?'}|{usuario or '?'}"


def registrar_intento_fallido(ip: Optional[str], usuario: Optional[str]) -> bool:
    """
    Registra un intento de login fallido. Devuelve True si la cuenta/IP se debe
    bloquear (se alcanzó el límite de intentos). Persiste en BD.
    """
    clave = _clave_bloqueo(ip, usuario)
    with _rate_lock:
        ahora = ahora_txt()
        hasta = None
        with db_connection(commit=True) as conn:
            r = None
            if usuario:
                r = conn.execute(
                    "SELECT id, intentos_fallidos, bloqueado_hasta FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                    (usuario,),
                ).fetchone()
            if r:
                nuevos = (r["intentos_fallidos"] or 0) + 1
                if nuevos >= LOGIN_MAX_ATTEMPTS:
                    from guias_coodescor.core.utils import sumar_segundos
                    hasta = sumar_segundos(ahora, LOGIN_LOCKOUT_SECONDS)
                    conn.execute(
                        "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
                        (nuevos, hasta, r["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE usuarios SET intentos_fallidos = ? WHERE id = ?",
                        (nuevos, r["id"]),
                    )
        _intentos_login[clave] = {"hasta": hasta}
        return hasta is not None


def esta_bloqueado(ip: Optional[str], usuario: Optional[str]) -> bool:
    """Indica si el usuario/IP está bloqueado por exceso de intentos fallidos."""
    if not usuario:
        return False
    with db_connection() as conn:
        r = conn.execute(
            "SELECT bloqueado_hasta FROM usuarios WHERE usuario = ? COLLATE NOCASE",
            (usuario,),
        ).fetchone()
        if r and r["bloqueado_hasta"]:
            if not fecha_pasada(r["bloqueado_hasta"]):
                return True
    return False


def generar_csrf_token() -> str:
    """Genera un token CSRF aleatorio."""
    return secrets.token_urlsafe(32)
