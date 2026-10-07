#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas API para gestión y búsqueda de clientes (tabla `clientes`, NIT PK).
Proporciona el endpoint para autocompletado del panel Ventas.
"""
from guias_coodescor.services.clientes_service import buscar_clientes
from guias_coodescor.core.logging_config import get_logger

_log = get_logger(__name__)


def _handler_buscar_clientes(qs, user, json_fn):
    """
    GET /api/clientes/buscar?q=<texto>&limite=<int>
    Requiere: cualquier sesión autenticada (401 si no).
    Retorna: {ok:True, resultados:[{nit,razon_social,direccion,ciudad,telefono,email,cliente_descubierto}...]}
    """
    if not user:
        return json_fn({"ok": False, "error": "Sesión inválida o expirada"}, 401)
    q = (qs.get("q") or [""])[0].strip()
    try:
        limite = int((qs.get("limite") or ["10"])[0])
        limite = max(1, min(50, limite))
    except (ValueError, TypeError):
        limite = 10
    if not q or len(q) < 1:
        return json_fn({"ok": True, "resultados": [], "query": q, "nota": "Escriba al menos 1 carácter (NIT, razón social, ciudad, teléfono...)"})
    filas = buscar_clientes(q, limite=limite)
    return json_fn({
        "ok": True,
        "resultados": filas,
        "query": q,
        "total": len(filas),
    })


RUTAS_CLIENTES_GET = [
    (r"^/api/clientes/buscar$", _handler_buscar_clientes),
]
