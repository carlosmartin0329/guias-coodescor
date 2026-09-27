#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio maestro de clientes (tabla clientes, PK = nit).

Reglas de integridad:
  - nit es PRIMARY KEY NOT NULL COLLATE NOCASE (único, insensible a mayúsculas).
  - Upsert inteligente por ORIGEN:
      * origen="manual"   (admin carga maestro): SIEMPRE sobreescribe campos no vacíos.
      * origen="descubierto" (Ventas crea guía con NIT nuevo):
        · Si el NIT NO existe → INSERT con cliente_descubierto=1.
        · Si el NIT EXISTE y cliente_descubierto=0 (maestro manual) → NO TOCAR NADA,
          para no sobreescribir datos oficiales con datos parciales de la guía.
        · Si el NIT EXISTE y cliente_descubierto=1 → actualiza solo campos NULL.

Ranking búsqueda (buscar_clientes):
  1. NIT exacto (igualdad COLLATE NOCASE) → puntuación máxima.
  2. NIT prefijo (LIKE q%).
  3. razón social prefijo (LIKE q%).
  4. razón social anywhere (LIKE %q%).
  5. ciudad prefijo / anywhere.
  6. teléfono / email anywhere.

100% stdlib. Sin dependencias externas (no pandas / sqlalchemy).
"""
import json
import logging
import re as _re
from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt
from guias_coodescor.database.connection import db_connection

_log = get_logger("guias_coodescor.clientes")

_CAMPOS_EDITABLES = [
    "razon_social", "direccion", "ciudad", "telefono", "email",
    "contacto", "forma_pago_default", "observaciones", "metadata",
]


def _normalizar_nit(nit: Optional[str]) -> str:
    """Normaliza NIT a sólo dígitos (sin puntos, guiones, espacios, leading zeros).

    Ejemplos:
      "800.000.000-1" → "8000000001"
      " 900100100-7 " → "9001001007"
      "NIT"        → ""
    """
    if not nit:
        return ""
    digitos = _re.sub(r"[^0-9]", "", str(nit))
    return digitos.lstrip("0")


# ---------------------------------------------------------------------------
# Lecturas simples
# ---------------------------------------------------------------------------
def obtener_cliente_por_nit(nit: str) -> Optional[Dict[str, Any]]:
    """Devuelve dict con los datos del cliente por NIT o None si no existe.

    Búsqueda COLLATE NOCASE (PK ya lo tiene, pero por si acaso).
    """
    nit_ok = _normalizar_nit(nit)
    if not nit_ok:
        return None
    with db_connection() as c:
        row = c.execute(
            "SELECT * FROM clientes WHERE nit = ? COLLATE NOCASE LIMIT 1",
            (nit_ok,),
        ).fetchone()
        return dict(row) if row else None


def listar_todos_clientes(limite: int = 5000) -> List[Dict[str, Any]]:
    """Devuelve todos los clientes (carga selectiva para exportaciones)."""
    with db_connection() as c:
        rows = c.execute(
            "SELECT * FROM clientes ORDER BY cliente_descubierto ASC, razon_social ASC LIMIT ?",
            (int(max(1, limite)),),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Escrituras: upsert inteligente por origen
# ---------------------------------------------------------------------------
def _limpiar_datos(datos: Dict[str, Any]) -> Dict[str, Any]:
    """Asegura que metadata sea string JSON, quita espacios alrededor de strings."""
    out: Dict[str, Any] = {}
    for k, v in (datos or {}).items():
        if k in ("nit",) or k in _CAMPOS_EDITABLES:
            if isinstance(v, str):
                v = v.strip()
                # no normalizar a '' strings de campos que aceptan NULL → None
                if v == "":
                    v = None
            out[k] = v
    if "metadata" in out:
        md = out["metadata"]
        if md is None:
            out["metadata"] = "{}"
        elif isinstance(md, (dict, list)):
            out["metadata"] = json.dumps(md, ensure_ascii=False)
        else:
            try:
                json.loads(str(md))
                out["metadata"] = str(md)
            except (TypeError, ValueError):
                out["metadata"] = "{}"
    return out


def guardar_cliente(
    datos: Dict[str, Any], origen: str = "manual",
) -> Tuple[bool, str, Optional[str]]:
    """Upsert inteligente. Devuelve (ok: bool, mensaje: str, nit_grabado: str|None).

    origen ∈ {"manual", "descubierto"}.
    """
    origen = str(origen or "manual").lower()
    if origen not in {"manual", "descubierto"}:
        origen = "manual"

    nit_raw = datos.get("nit")
    nit_ok = _normalizar_nit(nit_raw)
    if not nit_ok:
        return False, "NIT es obligatorio", None

    razon = (datos.get("razon_social") or "").strip()
    if not razon:
        if origen == "manual":
            return False, "razon_social es obligatorio para clientes manuales", nit_ok
        # descubierto permite razon por lo menos "(Sin nombre)"
        razon = f"(Cliente NIT {nit_ok})"

    limpio = _limpiar_datos({**datos, "nit": nit_ok, "razon_social": razon})
    ahora = ahora_txt()

    with db_connection(commit=True) as c:
        existente = c.execute(
            "SELECT * FROM clientes WHERE nit = ? COLLATE NOCASE LIMIT 1",
            (nit_ok,),
        ).fetchone()

        if not existente:
            # Insert nuevo
            cols = ["nit", "razon_social", "cliente_descubierto", "creado_en", "actualizado_en"]
            vals: List[Any] = [nit_ok, limpio.get("razon_social") or razon,
                               1 if origen == "descubierto" else 0, ahora, ahora]
            for campo in _CAMPOS_EDITABLES:
                if campo == "razon_social":
                    continue
                if campo in limpio:
                    cols.append(campo)
                    vals.append(limpio[campo])
            if "metadata" not in cols:
                cols.append("metadata")
                vals.append("{}")
            placeholders = ",".join("?" for _ in vals)
            c.execute(
                f"INSERT INTO clientes ({','.join(cols)}) VALUES ({placeholders})",
                vals,
            )
            _log.info("Cliente NIT=%s INSERTADO origen=%s", nit_ok, origen)
            return True, "Cliente creado", nit_ok

        # --- Ya existe → actualizar según reglas origen ---
        actual = dict(existente)
        es_descubierto_actual = bool(actual.get("cliente_descubierto"))

        if es_descubierto_actual and origen == "manual":
            # Promoción a manual. Guardar marca cliente_descubierto=0.
            nuevo_desc = 0
        elif not es_descubierto_actual and origen == "descubierto":
            # Manual existente → descubierto NO DEBE TOCARLO. Nada que hacer.
            _log.info("Cliente NIT=%s es maestro MANUAL. Descubierto sin cambios.", nit_ok)
            return True, "Cliente manual existente (sin cambios)", nit_ok
        else:
            # (manual + manual) o (descubierto + descubierto)
            nuevo_desc = int(es_descubierto_actual)

        sets: List[str] = ["actualizado_en = ?"]
        params: List[Any] = [ahora]
        sets.append("cliente_descubierto = ?")
        params.append(nuevo_desc)

        for campo in _CAMPOS_EDITABLES:
            if campo not in limpio:
                continue
            valor_nuevo = limpio[campo]
            if campo == "razon_social" and origen == "descubierto" and not es_descubierto_actual:
                continue  # no tocar manual
            valor_actual = actual.get(campo)
            if valor_nuevo is None:
                # No sobreescribir dato existente con NULL/empty
                # Excepto si origen=manual y venía explícitamente para borrar → en esta
                # implementación respetamos: si manual envía campo como None se ignora.
                continue
            if origen == "descubierto" and valor_actual not in (None, ""):
                # descubierto solo rellena NULLs
                continue
            sets.append(f"{campo} = ?")
            params.append(valor_nuevo)

        params.append(nit_ok)
        c.execute(
            f"UPDATE clientes SET {','.join(sets)} WHERE nit = ? COLLATE NOCASE",
            params,
        )
        _log.info("Cliente NIT=%s ACTUALIZADO origen=%s promovidomanual=%s",
                  nit_ok, origen, (not es_descubierto_actual and origen == "descubierto"))
        return True, "Cliente actualizado", nit_ok


# ---------------------------------------------------------------------------
# Hook llamado desde guias_service.crear_guia (NON-BLOCKING).
# Si falla, se loguea WARNING pero la guía se crea de todas formas (TRYCATCH afuera).
# ---------------------------------------------------------------------------
def asegurar_cliente_desde_ventas(
    nit: Optional[str],
    razon_social: Optional[str],
    direccion: Optional[str] = None,
    ciudad: Optional[str] = None,
    telefono: Optional[str] = None,
    email: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Asegura que exista un registro en clientes cuando Ventas crea una guía.

    Origen = "descubierto". Si NIT es vacío no hace nada.
    Devuelve (ok, nit_grabado).
    """
    nit_ok = _normalizar_nit(nit)
    if not nit_ok:
        return True, None
    payload: Dict[str, Any] = {
        "nit": nit_ok,
        "razon_social": (razon_social or "").strip() or None,
        "direccion": (direccion or "").strip() or None,
        "ciudad": (ciudad or "").strip() or None,
        "telefono": (telefono or "").strip() or None,
        "email": (email or "").strip() or None,
        "cliente_descubierto": 1,
    }
    ok, _msg, nit_g = guardar_cliente(payload, origen="descubierto")
    return ok, nit_g


# ---------------------------------------------------------------------------
# Búsqueda con ranking para autocompletado Ventas NIT.
# ---------------------------------------------------------------------------
def buscar_clientes(q: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Búsqueda con ranking (NIT exacto → prefijos → anywhere).

    Retorna lista ordenada por relevancia DESC, <= limite elementos.
    Cada dict incluye llaves: nit, razon_social, direccion, ciudad, telefono, email.
    """
    q = (str(q or "")).strip()
    limite = max(1, int(limite or 10))
    if not q:
        # si query vacía → descubiertos últimos
        with db_connection() as c:
            rows = c.execute(
                "SELECT nit, razon_social, direccion, ciudad, telefono, email "
                "FROM clientes ORDER BY actualizado_en DESC LIMIT ?",
                (limite,),
            ).fetchall()
            return [dict(r) for r in rows]

    q_upper = q.upper()
    q_like = f"%{q}%"
    q_prefix = f"{q}%"

    # Scores: lower = mejor
    CTE = """
    SELECT
      nit, razon_social, direccion, ciudad, telefono, email,
      CASE
        WHEN UPPER(nit) = ?                              THEN 1
        WHEN UPPER(nit) LIKE ?                           THEN 2
        WHEN UPPER(razon_social) LIKE ?                  THEN 3
        WHEN UPPER(razon_social) LIKE ?                  THEN 4
        WHEN UPPER(ciudad) LIKE ?                        THEN 5
        WHEN UPPER(ciudad) LIKE ?                        THEN 6
        WHEN UPPER(telefono) LIKE ?                      THEN 7
        WHEN UPPER(email) LIKE ?                         THEN 8
        ELSE 99
      END AS score
    FROM clientes
    WHERE
      UPPER(nit) LIKE ? OR
      UPPER(razon_social) LIKE ? OR
      UPPER(ciudad) LIKE ? OR
      UPPER(telefono) LIKE ? OR
      UPPER(email) LIKE ?
    """
    params = [
        q_upper,                # 1 igualdad nit
        q_prefix.upper(),       # 2 prefix nit
        q_prefix.upper(),       # 3 prefix razon
        q_like.upper(),         # 4 any razon
        q_prefix.upper(),       # 5 prefix ciudad
        q_like.upper(),         # 6 any ciudad
        q_like.upper(),         # 7 any telefono
        q_like.upper(),         # 8 any email
        # WHERE
        q_like.upper(),         # nit
        q_like.upper(),         # razon
        q_like.upper(),         # ciudad
        q_like.upper(),         # telefono
        q_like.upper(),         # email
    ]
    with db_connection() as c:
        rows = c.execute(
            f"{CTE} ORDER BY score ASC, cliente_descubierto ASC, razon_social ASC LIMIT ?",
            params + [limite],
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d.pop("score", None)
            out.append(d)
        return out


# ---------------------------------------------------------------------------
# Utilería administrativa (puede ser usado en carga masiva de clientes XLSX)
# ---------------------------------------------------------------------------
def eliminar_cliente(nit: str) -> Tuple[bool, str]:
    """Borra un cliente SÓLO si no tiene guías asociadas.
    (La FK guias.nit es ON DELETE SET NULL, así que la guía NO se borra.
     Aquí adicionalmente validamos que sea NIT con guías asociadas para
     evitar pérdida accidental de dato maestro.)
    """
    nit_ok = _normalizar_nit(nit)
    if not nit_ok:
        return False, "NIT inválido"
    with db_connection(commit=True) as c:
        cnt_guides = c.execute(
            "SELECT COUNT(1) FROM guias WHERE nit = ? COLLATE NOCASE",
            (nit_ok,),
        ).fetchone()[0]
        cnt_recp = c.execute(
            "SELECT COUNT(1) FROM receptores WHERE nit_cliente = ? COLLATE NOCASE",
            (nit_ok,),
        ).fetchone()[0]
        if cnt_guides > 0 or cnt_recp > 0:
            return False, f"No se puede borrar: {cnt_guides} guías y {cnt_recp} receptores asociados"
        c.execute("DELETE FROM clientes WHERE nit = ? COLLATE NOCASE", (nit_ok,))
        _log.warning("Cliente NIT=%s ELIMINADO (sin guías/receptores asociados)", nit_ok)
        return True, "Cliente eliminado"
