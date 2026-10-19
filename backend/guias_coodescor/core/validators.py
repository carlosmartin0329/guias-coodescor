#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validadores de entrada de datos para APIs y servicios.
Centraliza todas las validaciones de inputs del usuario.
"""
from typing import Any, Optional

from guias_coodescor.config import ROLES_VALIDOS
from guias_coodescor.core.utils import validar_nombre_usuario, validar_rol


class ValidationError(Exception):
    """Excepción lanzada cuando una validación de datos falla."""
    def __init__(self, mensaje: str, campo: Optional[str] = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


def requerir(valor: Any, campo: str, mensaje: Optional[str] = None) -> Any:
    """Valida que el campo no sea None, vacío, o compuesto sólo de espacios."""
    if valor is None:
        raise ValidationError(mensaje or f"El campo {campo} es obligatorio", campo)
    if isinstance(valor, str) and not valor.strip():
        raise ValidationError(mensaje or f"El campo {campo} no puede estar vacío", campo)
    return valor


def longitud_maxima(valor: str, campo: str, maximo: int) -> str:
    if isinstance(valor, str) and len(valor) > maximo:
        raise ValidationError(
            f"El campo {campo} no puede exceder {maximo} caracteres", campo
        )
    return valor


def longitud_minima(valor: str, campo: str, minimo: int) -> str:
    if isinstance(valor, str) and len(valor) < minimo:
        raise ValidationError(
            f"El campo {campo} debe tener al menos {minimo} caracteres", campo
        )
    return valor


def validar_entero_positivo(valor: Any, campo: str, por_def: int = 0) -> int:
    if valor in (None, ""):
        return por_def
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"El campo {campo} debe ser un número entero", campo)
    if n < 0:
        raise ValidationError(f"El campo {campo} no puede ser negativo", campo)
    return n


def validar_usuario(usuario: str) -> str:
    usuario = (usuario or "").strip()
    if not validar_nombre_usuario(usuario):
        raise ValidationError(
            "Formato de usuario inválido. Use 3-50 caracteres alfanuméricos o . _ - @",
            "usuario",
        )
    return usuario


def validar_nombre_persona(nombre: str) -> str:
    nombre = (nombre or "").strip()
    if not nombre or len(nombre) < 2:
        raise ValidationError("Nombre demasiado corto (mínimo 2 caracteres)", "nombre")
    if len(nombre) > 120:
        raise ValidationError("Nombre demasiado largo (máximo 120 caracteres)", "nombre")
    return nombre


def validar_clave_nueva(clave: str) -> str:
    from guias_coodescor.core.security import validar_password_fuerte
    clave = clave or ""
    error = validar_password_fuerte(clave)
    if error:
        raise ValidationError(error, "clave")
    return clave


def validar_rol_input(rol: str) -> str:
    rol = (rol or "").strip().lower()
    if not validar_rol(rol):
        raise ValidationError(
            f"Rol inválido. Válidos: {', '.join(sorted(ROLES_VALIDOS))}", "rol"
        )
    return rol


def validar_consecutivo(valor: Any) -> int:
    return validar_entero_positivo(valor, "consecutivo", 1)


def validar_estado_guia(estado: str) -> str:
    from guias_coodescor.config import ESTADOS
    estado = (estado or "").strip().upper()
    if estado and estado not in ESTADOS:
        raise ValidationError(f"Estado no reconocido: {estado}", "estado")
    return estado
