#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de receptores (temporal). Almacena PII cifrada en archivo separado,
relacionada con clientes por NIT (FK) y guías por id (FK cruzada validada en
servicio porque SQLite no soporta FK cross-database).

Políticas:
  - Integridad 0 huérfanos: antes de INSERT/UPDATE, service-layer valida:
      (a) nit_cliente EXISTE en guias.db.clientes
      (b) si guia_relacionada_id is not None → EXISTE en guias.db.guias
  - Permisos granular:
      admin/administrativo/cedis → CRUD completo
      transportador → SOLO LECTURA de receptores de SUS guías asignadas
      ventas → 403 nada
  - TTR: receptor.vence_en < ahora → purga FÍSICA cada 60 min.
"""
import logging
import re as _re_nit
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt, fecha_pasada, sumar_segundos
from guias_coodescor.database.connection import (
    db_connection,
    receptores_db_connection,
)
from guias_coodescor.database.models import obtener_o_generar_receptores_secret
from guias_coodescor.services.crypto_service import cifrar_valor, descifrar_valor

_log = get_logger("guias_coodescor.receptores")

_CAMPOS_CIF = ["nombres_apellidos", "numero_doc", "telefono", "email"]
_TIPOS_DOC = {"CC", "CE", "TI", "PAS", "NIT", "RC", "Otro"}


def _normalizar_nit(nit: Any) -> str:
    """Normaliza NIT: solo dígitos, quita leading zeros.
    Mismo algoritmo que clientes_service._normalizar_nit para evitar falsos negativos
    en la validación FK cruzada.
    """
    if not nit:
        return ""
    digitos = _re_nit.sub(r"[^0-9]", "", str(nit))
    return digitos.lstrip("0")


def _cifrar_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    master = obtener_o_generar_receptores_secret()
    out = {}
    for campo in _CAMPOS_CIF:
        valor = data.get(campo)
        col = f"{campo}_cif"
        out[col] = cifrar_valor(valor, master) if valor not in (None, "") else ""
    return out


def _descifrar_row(row) -> Dict[str, Any]:
    if not row:
        return {}
    master = obtener_o_generar_receptores_secret()
    d = dict(row)
    for campo in _CAMPOS_CIF:
        col_cif = f"{campo}_cif"
        d[campo] = descifrar_valor(d.get(col_cif) or "", master)
    return d


def _validar_fk_pre_insert(payload: Dict[str, Any]) -> Optional[str]:
    nit_cliente = _normalizar_nit(payload.get("nit_cliente"))
    guia_relacionada_id = payload.get("guia_relacionada_id")
    if not nit_cliente:
        return "nit_cliente obligatorio"
    cliente_ok = False
    with db_connection() as conn:
        existe = conn.execute(
            "SELECT count(*) FROM clientes WHERE nit = ? COLLATE NOCASE",
            (nit_cliente,),
        ).fetchone()[0]
        cliente_ok = existe >= 1
    if not cliente_ok:
        # Intentamos sin normalizar (búsqueda tolerant)
        with db_connection() as conn:
            raw_nit = (str(payload.get("nit_cliente") or "")).strip()
            existe2 = conn.execute(
                "SELECT count(*) FROM clientes WHERE nit = ? COLLATE NOCASE",
                (raw_nit,),
            ).fetchone()[0]
            cliente_ok = existe2 >= 1
        if not cliente_ok:
            return f"NIT cliente '{raw_nit}' NO existe en tabla clientes"
    if guia_relacionada_id is not None and str(guia_relacionada_id).isdigit():
        gid = int(guia_relacionada_id)
        with db_connection() as conn:
            existe = conn.execute(
                "SELECT count(*) FROM guias WHERE id = ?", (gid,)
            ).fetchone()[0]
        if existe < 1:
            return f"La guía {gid} NO existe (no se puede ligar receptor huérfano)"
    return None


def _calcular_vence_en(guia_relacionada_id: Optional[int]) -> str:
    if guia_relacionada_id is None:
        return sumar_segundos(ahora_txt(), 30 * 86400)
    with db_connection() as conn:
        estado = None
        entregado_en = None
        r = conn.execute(
            "SELECT estado FROM guias WHERE id = ?", (guia_relacionada_id,)
        ).fetchone()
        if not r:
            return sumar_segundos(ahora_txt(), 30 * 86400)
        estado = r["estado"]
        ev = conn.execute(
            """
            SELECT datos, en FROM eventos
            WHERE guia_id = ? AND tipo = 'entrega_cliente'
            ORDER BY id DESC LIMIT 1
            """,
            (guia_relacionada_id,),
        ).fetchone()
        if ev:
            entregado_en = ev["en"]
    if estado == "ENTREGADA" and entregado_en:
        try:
            base = entregado_en
            delta = 7 * 86400
            return sumar_segundos(base, delta)
        except Exception:
            return sumar_segundos(ahora_txt(), 7 * 86400)
    return sumar_segundos(ahora_txt(), 30 * 86400)


def registrar_receptor(
    usuario_actual: Dict[str, Any],
    payload: Dict[str, Any],
    ip: Optional[str] = None,
    dispositivo: Optional[str] = None,
) -> Tuple[bool, Any, str, Optional[Dict[str, Any]]]:
    """Crea un receptor nuevo.

    Firma (mantenida con routes_receptores.py y test_clientes_receptores.py):
      Params: usuario_actual PRIMERO, luego payload, luego ip/dispositivo.
      Retorna: (ok:bool, codigo:int|str, msg:str, data:dict|None)

    Integridad 0 huérfanos: valida FK nit_cliente→clientes AND guia_id→guias.
    Permisos: admin/administrativo/cedis.
    """
    if not usuario_actual:
        return False, 401, "Sesión requerida", None
    rol = (usuario_actual.get("rol") or "").lower()
    if rol not in {"admin", "administrativo", "cedis"}:
        return False, 403, "Permiso insuficiente", None
    nombres = (str(payload.get("nombres_apellidos") or "")).strip()
    tipo_doc = (str(payload.get("tipo_doc") or "CC")).strip().upper()
    numero_doc = (str(payload.get("numero_doc") or "")).strip()
    if not nombres:
        return False, 400, "nombres_apellidos obligatorio", None
    if tipo_doc not in _TIPOS_DOC:
        tipo_doc = "Otro"
    if not numero_doc:
        return False, 400, "numero_doc obligatorio", None
    nit_cliente = _normalizar_nit(payload.get("nit_cliente"))
    guia_relacionada_id = payload.get("guia_relacionada_id")
    if guia_relacionada_id in (None, "", "None"):
        guia_relacionada_id = None
    elif str(guia_relacionada_id).isdigit():
        guia_relacionada_id = int(guia_relacionada_id)
    else:
        return False, 400, "guia_relacionada_id debe ser entero", None
    payload_normalizado = {
        "nit_cliente": nit_cliente,
        "nombres_apellidos": nombres,
        "tipo_doc": tipo_doc,
        "numero_doc": numero_doc,
        "telefono": (str(payload.get("telefono") or "")).strip() or None,
        "email": (str(payload.get("email") or "")).strip() or None,
        "relacion_con_cliente": (str(payload.get("relacion_con_cliente") or "")).strip() or None,
        "guia_relacionada_id": guia_relacionada_id,
        "ip_registro": (ip or "").strip() or None,
        "dispositivo_registro": (dispositivo or "").strip() or None,
    }
    err_fk = _validar_fk_pre_insert(payload_normalizado)
    if err_fk:
        # Retorna str-code FK_NIT_NO_EXISTE / FK_GUIA_NO_EXISTE si aplica
        cod = "FK_NIT_NO_EXISTE" if "NO existe en tabla clientes" in err_fk else \
              ("FK_GUIA_NO_EXISTE" if "NO existe (no se puede ligar" in err_fk else 400)
        return False, cod, err_fk, None
    cifrados = _cifrar_payload(payload_normalizado)
    ahora = ahora_txt()
    vence_en = _calcular_vence_en(guia_relacionada_id)
    try:
        with receptores_db_connection(commit=True) as conn:
            cur = conn.execute(
                """
                INSERT INTO receptores(
                    nit_cliente,
                    nombres_apellidos_cif,
                    tipo_doc,
                    numero_doc_cif,
                    telefono_cif,
                    email_cif,
                    relacion_con_cliente,
                    registrado_por,
                    registrado_en,
                    vence_en,
                    guia_relacionada_id
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    nit_cliente,
                    cifrados["nombres_apellidos_cif"],
                    tipo_doc,
                    cifrados["numero_doc_cif"],
                    cifrados.get("telefono_cif") or "",
                    cifrados.get("email_cif") or "",
                    payload_normalizado.get("relacion_con_cliente"),
                    str(usuario_actual.get("usuario") or ""),
                    ahora,
                    vence_en,
                    guia_relacionada_id,
                ),
            )
            return True, 201, "Receptor registrado", {
                "id_temp": cur.lastrowid,
                "vence_en": vence_en,
            }
    except Exception as ex:
        return False, 500, f"Error interno: {ex}", None


def _tiene_acceso_receptor_guia(usuario_actual, guia_relacionada_id: Optional[int]) -> bool:
    if not usuario_actual:
        return False
    rol = (usuario_actual.get("rol") or "").lower()
    if rol in {"admin", "administrativo", "cedis"}:
        return True
    if rol == "transportador":
        if not guia_relacionada_id:
            return False
        with db_connection() as conn:
            r = conn.execute(
                "SELECT transportador_asignado_id FROM guias WHERE id = ?",
                (guia_relacionada_id,),
            ).fetchone()
        if not r or r["transportador_asignado_id"] is None:
            return False
        asignado = r["transportador_asignado_id"]
        return asignado == usuario_actual.get("id")
    return False


def listar_por_nit(usuario_actual, nit_cliente: str) -> List[Dict[str, Any]]:
    """Lista receptores por NIT. Orden usuario PRIMERO (igual routes_receptores).

    Permisos: admin/adm/cedis → todo; transportador → solo sus guías asignadas
    (filtrado adicionalmente a nivel UI cuando es necesario; aquí devuelve
    receptores del NIT y luego el transportador filtra por sus guías).
    """
    nit_norm = _normalizar_nit(nit_cliente)
    if not _tiene_acceso_receptor_guia(usuario_actual, None):
        if (usuario_actual or {}).get("rol") == "transportador":
            # Transportador ve SUS guias asignadas pertenecientes al nit.
            if not nit_norm:
                return []
            with db_connection() as conn:
                mis_ids = [
                    r[0] for r in conn.execute(
                        "SELECT id FROM guias WHERE transportador_asignado_id = ?",
                        (int(usuario_actual.get("id") or 0),),
                    ).fetchall()
                ]
            if not mis_ids:
                return []
            with receptores_db_connection() as conn:
                qmarks = ",".join("?" for _ in mis_ids)
                rows = conn.execute(
                    f"SELECT * FROM receptores WHERE (nit_cliente = ? COLLATE NOCASE OR nit_cliente = ? COLLATE NOCASE) "
                    f"AND guia_relacionada_id IN ({qmarks}) ORDER BY id_temp DESC LIMIT 100",
                    [nit_norm, (nit_cliente or "").strip()] + mis_ids,
                ).fetchall()
            return [_descifrar_row(r) for r in rows]
        return []
    if not nit_norm:
        return []
    with receptores_db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM receptores WHERE nit_cliente = ? COLLATE NOCASE OR nit_cliente = ? COLLATE NOCASE "
            "ORDER BY id_temp DESC LIMIT 100",
            (nit_norm, (nit_cliente or "").strip()),
        ).fetchall()
    return [_descifrar_row(r) for r in rows]


def obtener_por_guia(usuario_actual, guia_relacionada_id: int) -> Tuple[bool, int, str, Optional[Dict[str, Any]]]:
    """Retorna (ok, code, msg, data). Orden usuario PRIMERO."""
    if not _tiene_acceso_receptor_guia(usuario_actual, int(guia_relacionada_id)):
        return False, 403, "Permiso insuficiente para esta guía", None
    with receptores_db_connection() as conn:
        r = conn.execute(
            "SELECT * FROM receptores WHERE guia_relacionada_id = ? ORDER BY id_temp DESC LIMIT 1",
            (int(guia_relacionada_id),),
        ).fetchone()
    if not r:
        return True, 200, "Sin receptor", None
    return True, 200, "OK", _descifrar_row(r)


def purgar_receptores_vencidos() -> int:
    """Elimina físicamente todos los receptores vencidos.
    Escribe evento 'receptor_purgado' en guias.eventos (solo cuando la guía
    existe y el guia_relacionada_id es not null — trazabilidad SIN PII).
    Retorna número de registros purgados.
    """
    ahora = ahora_txt()
    purgados = []
    with receptores_db_connection() as conn:
        rows = conn.execute(
            "SELECT id_temp, guia_relacionada_id FROM receptores WHERE vence_en <= ?",
            (ahora,),
        ).fetchall()
        purgados = [(int(r["id_temp"]), r["guia_relacionada_id"]) for r in rows]
        if purgados:
            conn.execute("DELETE FROM receptores WHERE vence_en <= ?", (ahora,))
            conn.commit()
    from guias_coodescor.services.eventos_service import agregar_evento

    for _id_temp, gid in purgados:
        if gid is None:
            continue
        try:
            agregar_evento(
                guia_id=int(gid),
                tipo="receptor_purgado",
                user={"usuario": "sistema", "rol": "sistema"},
                datos={
                    "receptor_id_temp": int(_id_temp),
                    "motivo": "purga_TTR_vencido_7d_postentrega_o_30d_natural",
                    "purgado_en": ahora_txt(),
                },
            )
        except Exception as _e_p:
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.getLogger(__name__).debug(
                    "Evento receptor_purgado no guardado guia=%s: %s",
                    gid, _e_p,
                )
    return len(purgados)


def eliminar_receptor(usuario_actual, id_temp: int) -> Tuple[bool, str]:
    """Elimina un receptor. Orden usuario PRIMERO. Retorna (ok, msg).

    Sólo admin (403 resto). El borrado es FÍSICO (cumplimiento GDPR).
    """
    rol = (usuario_actual or {}).get("rol") or ""
    if rol != "admin":
        return False, "Solo admin puede eliminar receptores"
    with receptores_db_connection(commit=True) as conn:
        conn.execute("DELETE FROM receptores WHERE id_temp = ?", (int(id_temp),))
    return True, "Receptor eliminado"
