#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de autenticación y gestión de usuarios.
Centraliza login, logout, creación de usuarios y cambio de estado.
"""
import sqlite3
from typing import Optional

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.security import (
    borrar_sesion,
    cookie_set_sid,
    cookie_unset_sid,
    crear_sesion,
    esta_bloqueado,
    hash_password,
    registrar_intento_fallido,
    verificar_password,
)
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.core.validators import (
    ValidationError,
    requerir,
    validar_clave_nueva,
    validar_nombre_persona,
    validar_rol_input,
    validar_usuario,
)
from guias_coodescor.database.connection import db_connection
from guias_coodescor.database.models import get_config, set_config

logger = get_logger("guias_coodescor.auth")


class AuthError(Exception):
    pass


class ForbiddenError(Exception):
    pass


def login(usuario: str, clave: str, ip: Optional[str] = None, user_agent: Optional[str] = None):
    """
    Intenta autenticar a un usuario. Devuelve (sid, cookie_header, usuario_dict).
    Lanza AuthError en caso de credenciales incorrectas o bloqueo.
    """
    usuario = (usuario or "").strip()

    if esta_bloqueado(ip, usuario):
        logger.warning("Intento de login con cuenta bloqueada: usuario=%s ip=%s", usuario, ip)
        raise AuthError("Cuenta temporalmente bloqueada por demasiados intentos fallidos. Intente más tarde.")

    if not usuario or not clave:
        registrar_intento_fallido(ip, usuario)
        raise AuthError("Usuario o contraseña inválidos")

    with db_connection() as conn:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? COLLATE NOCASE AND activo = 1",
            (usuario,),
        ).fetchone()

        if not fila:
            registrar_intento_fallido(ip, usuario)
            logger.info("Login fallido: usuario no existe o inactivo (%s) ip=%s", usuario, ip)
            raise AuthError("Usuario o contraseña inválidos")

        if fila["bloqueado_hasta"]:
            from guias_coodescor.core.utils import fecha_pasada
            if not fecha_pasada(fila["bloqueado_hasta"]):
                logger.warning("Login bloqueado: usuario=%s ip=%s", usuario, ip)
                raise AuthError("Cuenta temporalmente bloqueada. Intente más tarde.")

        if not verificar_password(clave, fila["pass_hash"], fila["sal"]):
            registrar_intento_fallido(ip, fila["usuario"])
            logger.info("Login fallido: contraseña incorrecta (%s) ip=%s", fila["usuario"], ip)
            raise AuthError("Usuario o contraseña inválidos")

    sid = crear_sesion(fila["id"], ip=ip, user_agent=user_agent)
    cookie = cookie_set_sid(sid)
    logger.info("Login exitoso: usuario=%s ip=%s", fila["usuario"], ip)
    return sid, cookie, dict(fila)


def logout(sid: str) -> str:
    borrar_sesion(sid)
    logger.info("Logout de sesión %s", sid[:8] + "..." if sid else "")
    return cookie_unset_sid()


def requerir_rol(user: dict, *roles):
    if not user:
        raise ForbiddenError("Sesión inválida o expirada")
    if roles and user.get("rol") not in roles:
        raise ForbiddenError("No tiene permisos para realizar esta acción")
    return True


def crear_usuario(
    usuario: str,
    nombre: str,
    clave: str,
    rol: str,
    creador: Optional[dict] = None,
) -> int:
    """
    Crea un usuario nuevo en BD. Devuelve el ID insertado.
    Requiere que el creador tenga rol admin (validar externamente si es necesario).
    """
    usuario = validar_usuario(usuario)
    nombre = validar_nombre_persona(nombre)
    clave = validar_clave_nueva(clave)
    rol = validar_rol_input(rol)

    pass_hash, sal = hash_password(clave)
    ahora = ahora_txt()
    try:
        with db_connection(commit=True) as conn:
            cur = conn.execute(
                """
                INSERT INTO usuarios(usuario, nombre, pass_hash, sal, rol, creado)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (usuario, nombre, pass_hash, sal, rol, ahora),
            )
            uid = cur.lastrowid
        logger.info("Usuario creado id=%s usuario=%s rol=%s creador=%s",
                    uid, usuario, rol, (creador or {}).get("usuario", "?"))
        return uid
    except sqlite3.IntegrityError as ex:
        raise ValidationError("Ese nombre de usuario ya existe", "usuario") from ex


def listar_usuarios():
    with db_connection() as conn:
        filas = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        return [dict(r) for r in filas]


def actualizar_configuracion(datos: dict, admin_user: dict) -> None:
    requerir_rol(admin_user, "admin")
    with db_connection(commit=True) as conn:
        for clave in ("siguiente", "pie", "empresa"):
            if clave in datos:
                valor = str(datos[clave]) if datos[clave] is not None else ""
                conn.execute(
                    "INSERT OR REPLACE INTO config(clave, valor) VALUES (?, ?)",
                    (clave, valor),
                )
    logger.info("Configuración actualizada por %s", admin_user.get("usuario"))


def cambiar_clave_propia(user: dict, clave_actual: str, clave_nueva: str) -> None:
    """
    Permite a un usuario cambiar su propia contraseña.
    Verifica la clave actual para que una sesión abierta no baste para
    comprometer la cuenta, e invalida el resto de sesiones.
    """
    usuario_id = user.get("id")
    if not usuario_id:
        raise AuthError("Sesión inválida o expirada")
    clave_nueva = validar_clave_nueva(clave_nueva)

    with db_connection() as conn:
        fila = conn.execute(
            "SELECT pass_hash, sal FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
    if not fila or not verificar_password(clave_actual, fila["pass_hash"], fila["sal"]):
        raise AuthError("La contraseña actual no es correcta")

    _aplicar_cambio_clave(usuario_id, clave_nueva)
    logger.info("Contraseña propia actualizada: usuario=%s", user.get("usuario"))


def restablecer_clave(admin_user: dict, usuario_objetivo: str, clave_nueva: str) -> None:
    """
    Un admin restablece la contraseña de otro usuario (usuario olvidado).
    Cierra todas las sesiones del usuario afectado.
    """
    requerir_rol(admin_user, "admin")
    clave_nueva = validar_clave_nueva(clave_nueva)
    with db_connection() as conn:
        fila = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ? COLLATE NOCASE",
            ((usuario_objetivo or "").strip(),),
        ).fetchone()
    if not fila:
        raise ValidationError("Ese usuario no existe", "usuario")
    _aplicar_cambio_clave(fila["id"], clave_nueva)
    logger.info(
        "Contraseña restablecida por %s para usuario=%s",
        admin_user.get("usuario"),
        usuario_objetivo,
    )


def _aplicar_cambio_clave(usuario_id: int, clave_nueva: str) -> None:
    pass_hash, sal = hash_password(clave_nueva)
    with db_connection(commit=True) as conn:
        conn.execute(
            "UPDATE usuarios SET pass_hash = ?, sal = ?, intentos_fallidos = 0, bloqueado_hasta = NULL "
            "WHERE id = ?",
            (pass_hash, sal, usuario_id),
        )
        # Cerrar las otras sesiones abiertas evita que un robo de credenciales
        # sobreviva al cambio de contraseña.
        conn.execute("DELETE FROM sesiones WHERE usuario_id = ?", (usuario_id,))


def obtener_config(clave: str, por_def: str = "") -> str:
    return get_config(clave, por_def)


def guardar_config(clave: str, valor: str) -> None:
    set_config(clave, valor)
