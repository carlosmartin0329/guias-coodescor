#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Confirmación externa gratuita con Google Apps Script.

- Genera un link firmado (guía, cliente, emisión y vencimiento de 7 días).
- Consulta las confirmaciones pendientes en Google Apps Script.
- Cierra automáticamente las guías EN_RUTA del flujo normal.
- Nunca depende de internet para la operación interna: si Google no está
  accesible, deja la confirmación pendiente y registra el error para seguimiento.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import guias_coodescor.config as config
from guias_coodescor.core.validators import ValidationError
from guias_coodescor.database.connection import db_connection
from guias_coodescor.services.auth_service import ForbiddenError
from guias_coodescor.services.guias_service import (
    obtener_guia,
    procesar_evento,
)

logger = logging.getLogger("guias_coodescor.confirmaciones_link")

USUARIO_SISTEMA = {
    "id": None,
    "usuario": "sistema_link",
    "nombre": "Confirmación link externo",
    "rol": "admin",
}


def _b64url(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _firmar(payload_b64: str) -> str:
    secreto = str(getattr(config, "CONFIRMACION_TOKEN_SECRET", "") or "")
    if not secreto:
        raise ValidationError(
            "Falta configurar COODESCOR_CONFIRMACION_TOKEN_SECRET para generar links."
        )
    firma = hmac.new(
        secreto.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256
    ).digest()
    return _b64url(firma)


def generar_token(guia: Dict[str, Any]) -> str:
    ahora = int(datetime.now().timestamp())
    exp = ahora + 7 * 24 * 60 * 60
    payload = {
        "g": int(guia["id"]),
        "n": guia.get("consecutivo") or "",
        "c": guia.get("cliente") or "",
        "iat": ahora,
        "exp": exp,
    }
    payload_b64 = _b64url(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    return f"{payload_b64}.{_firmar(payload_b64)}"


def _url_base() -> str:
    url = str(getattr(config, "CONFIRMACION_URL", "") or "").strip()
    if not url:
        raise ValidationError(
            "Falta configurar COODESCOR_CONFIRMACION_URL con la URL del Web App de Google."
        )
    return url


def generar_link(guia_id: int, user: Dict[str, Any]) -> Dict[str, Any]:
    rol = (user or {}).get("rol")
    if rol not in ("ventas", "administrativo"):
        raise ForbiddenError(
            "El link de confirmación solo lo generan los perfiles Ventas y Administrativo."
        )
    guia = obtener_guia(int(guia_id))
    if not guia:
        raise ValidationError("La guía no existe", "guia_id")
    if guia.get("estado") in ("ENTREGADA", "ANULADA"):
        raise ValidationError("No se puede generar un link para una guía cerrada.")
    if guia.get("envio_directo_cedis"):
        raise ValidationError(
            "El link de confirmación aplica al flujo normal. El flujo directo lo cierra CEDIS."
        )
    url = _url_base()

    with db_connection() as conn:
        existente = conn.execute(
            "SELECT * FROM confirmaciones_link WHERE guia_id = ?", (int(guia_id),)
        ).fetchone()
    if existente:
        expira = str(existente["expira_en"] or "")
        if existente["estado"] in ("aplicada", "duplicada"):
            raise ValidationError("Esta guía ya tiene una confirmación procesada.")
        if expira and expira < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
            raise ValidationError(
                "El link de esta guía venció. Genera un link nuevo desde soporte."
            )
        return {
            "ok": True,
            "ya_emitido": True,
            "link": existente["link"],
            "token": existente["token"],
            "expira_en": existente["expira_en"],
        }

    token = generar_token(guia)
    link = f"{url}{'&' if '?' in url else '?'}t={urllib.parse.quote(token)}"
    expira = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_connection(commit=True) as conn:
        conn.execute(
            """
            INSERT INTO confirmaciones_link
              (guia_id, token, link, creado_por, creado_rol, creado_en, expira_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(guia_id), token, link, (user or {}).get("id"),
                rol, ahora, expira,
            ),
        )
    return {
        "ok": True,
        "ya_emitido": False,
        "link": link,
        "token": token,
        "expira_en": expira,
    }


def _llamar_google(params: Dict[str, Any]) -> Dict[str, Any]:
    url = _url_base()
    secreto = str(getattr(config, "CONFIRMACION_SYNC_SECRET", "") or "")
    if not secreto:
        raise ValidationError(
            "Falta configurar COODESCOR_CONFIRMACION_SYNC_SECRET para sincronizar."
        )
    consulta = dict(params)
    consulta["secret"] = secreto
    destino = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(consulta)}"
    with urllib.request.urlopen(destino, timeout=15) as respuesta:
        cuerpo = respuesta.read().decode("utf-8", errors="replace")
    try:
        datos = json.loads(cuerpo)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Google Apps Script devolvió una respuesta inválida: {cuerpo[:200]}") from exc
    if not datos.get("ok"):
        raise RuntimeError(str(datos.get("error") or "Error consultando Google Apps Script"))
    return datos


def _marcar_google(confirmacion_id: str, estado: str, detalle: str = "") -> bool:
    if not confirmacion_id:
        return False
    try:
        _llamar_google({
            "accion": "marcar",
            "id": confirmacion_id,
            "estado": estado,
            "detalle": detalle[:500],
        })
        return True
    except Exception as exc:  # la marca es best-effort; no perder el cierre local
        logger.warning("No se pudo marcar la confirmación %s en Google: %s", confirmacion_id, exc)
        return False


def _actualizar_local(guia_id: int, **campos: Any) -> None:
    if not campos:
        return
    sets = ", ".join(f"{campo} = ?" for campo in campos)
    with db_connection(commit=True) as conn:
        conn.execute(
            f"UPDATE confirmaciones_link SET {sets} WHERE guia_id = ?",
            list(campos.values()) + [int(guia_id)],
        )


def sincronizar_confirmaciones() -> Dict[str, Any]:
    """
    Consulta pendientes en Google y aplica las que corresponden.
    No lanza excepción por falta de internet: devuelve el error en el resultado.
    """
    stats = {"revisadas": 0, "aplicadas": 0, "duplicadas": 0, "errores": 0}
    try:
        datos = _llamar_google({"accion": "pendientes"})
    except Exception as exc:
        logger.warning("Sincronización de confirmaciones no disponible: %s", exc)
        return {**stats, "ok": False, "error": str(exc)}

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for item in datos.get("pendientes") or []:
        stats["revisadas"] += 1
        guia_id = int(item.get("guia_id") or 0)
        confirmacion_id = str(item.get("id") or "")
        nombre = str(item.get("nombre") or "").strip()[:120]
        observaciones = str(item.get("observaciones") or "").strip()[:1000]
        if not guia_id:
            continue
        guia = obtener_guia(guia_id)
        if not guia:
            stats["errores"] += 1
            _actualizar_local(
                guia_id, estado="error", detalle="La guía no existe", aplicado_en=ahora
            )
            _marcar_google(confirmacion_id, "error", "La guía no existe")
            continue

        if guia.get("estado") in ("ENTREGADA", "ANULADA"):
            stats["duplicadas"] += 1
            _actualizar_local(
                guia_id,
                confirmacion_id=confirmacion_id or None,
                fecha_confirmacion=item.get("fecha_confirmacion"),
                nombre=nombre,
                observaciones=observaciones,
                estado="duplicada",
                aplicado_en=ahora,
                detalle="La guía ya estaba cerrada",
            )
            _marcar_google(confirmacion_id, "duplicada", "La guía ya estaba cerrada")
            continue

        if guia.get("envio_directo_cedis") or guia.get("estado") != "EN_RUTA":
            stats["errores"] += 1
            detalle = (
                "El link solo cierra guías EN_RUTA del flujo normal"
                f" (estado actual: {guia.get('estado')})."
            )
            _actualizar_local(
                guia_id,
                confirmacion_id=confirmacion_id or None,
                fecha_confirmacion=item.get("fecha_confirmacion"),
                nombre=nombre,
                observaciones=observaciones,
                estado="error",
                aplicado_en=ahora,
                detalle=detalle,
            )
            _marcar_google(confirmacion_id, "error", detalle)
            continue

        try:
            procesar_evento(
                guia_id,
                "entrega_cliente",
                USUARIO_SISTEMA,
                {
                    "recibe": nombre or "Cliente",
                    "obs": observaciones,
                    "origen_link": True,
                    "confirmacion_id": confirmacion_id,
                    "fecha_confirmacion": item.get("fecha_confirmacion") or ahora,
                },
                dispositivo="google_form",
                ip="google",
            )
            stats["aplicadas"] += 1
            _actualizar_local(
                guia_id,
                confirmacion_id=confirmacion_id or None,
                fecha_confirmacion=item.get("fecha_confirmacion"),
                nombre=nombre,
                observaciones=observaciones,
                estado="aplicada",
                aplicado_en=ahora,
                detalle="Cierre automático por confirmación externa",
            )
            _marcar_google(confirmacion_id, "aplicada", "Cierre automático Coodescor")
        except Exception as exc:
            stats["errores"] += 1
            logger.warning("No se pudo aplicar confirmación de guía %s: %s", guia_id, exc)
            _actualizar_local(
                guia_id,
                confirmacion_id=confirmacion_id or None,
                fecha_confirmacion=item.get("fecha_confirmacion"),
                nombre=nombre,
                observaciones=observaciones,
                estado="error",
                aplicado_en=ahora,
                detalle=str(exc)[:500],
            )
            _marcar_google(confirmacion_id, "error", str(exc)[:500])

    return {**stats, "ok": True}


def listar_confirmaciones(limite: int = 100) -> List[Dict[str, Any]]:
    limite = max(1, min(500, int(limite or 100)))
    with db_connection() as conn:
        filas = conn.execute(
            """
            SELECT c.*, g.consecutivo, g.estado AS guia_estado, g.cliente AS guia_cliente
            FROM confirmaciones_link c
            LEFT JOIN guias g ON g.id = c.guia_id
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
        return [dict(fila) for fila in filas]
