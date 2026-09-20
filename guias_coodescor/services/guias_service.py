#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de negocio para guías: CRUD, búsqueda, validación de transiciones
de estado y permisos.
"""
from typing import Any, Dict, List, Optional, Tuple

from guias_coodescor.config import (
    ESTADO_ESPERADO_POR_EVENTO,
    ESTADOS,
    PERMISO,
    PERMISO_ADICIONAL_ROL,
    TRANSICION,
)
from guias_coodescor.core.logging_config import get_logger
from guias_coodescor.core.utils import ahora_txt, codigo_verificacion
from guias_coodescor.core.validators import (
    ValidationError,
    longitud_maxima,
    requerir,
    validar_estado_guia,
)
from guias_coodescor.database.connection import db_connection, get_db_lock
from guias_coodescor.database.models import get_config
from guias_coodescor.services.auth_service import ForbiddenError, requerir_rol
from guias_coodescor.services.eventos_service import agregar_evento

logger = get_logger("guias_coodescor.guias")


class GuiaNoExisteError(Exception):
    pass


class EstadoInvalidoError(Exception):
    pass


def _parsear_estado_error(e):
    return str(e)


def _bool_flag(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "si", "s", "on", "yes"}
    return False


def siguiente_consecutivo() -> int:
    with db_connection() as conn:
        actual = int(get_config("siguiente", "1"))
    return actual


def crear_guia(
    user: dict,
    datos_guia: Dict[str, Any],
    dispositivo: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Crea una nueva guía (solo rol ventas).
    - SIN FIRMA DE VENTAS (la identidad la da el usuario autenticado).
    - Si la casilla 'envio_directo_cedis' = True, automáticamente pasa el estado
      a EN_CEDIS (salta el paso de recepción Administrativa).
    - Pre-llena datos de transportador, persona que recibe EN CLIENTE, y los
      CAMPOS DE BULTOS (cajas/bolsas/cayvas/sobres/totales); CEDIS confirmará/editará.
    Devuelve (guia_id, consecutivo).
    """
    requerir_rol(user, "ventas")

    cliente = requerir(datos_guia.get("cliente"), "cliente")
    ciudad = requerir(datos_guia.get("ciudad"), "ciudad")
    cliente = longitud_maxima(str(cliente).strip(), "cliente", 200)
    ciudad = longitud_maxima(str(ciudad).strip(), "ciudad", 120)
    direccion = longitud_maxima(str(datos_guia.get("direccion") or "").strip(), "direccion", 300)
    documentos = longitud_maxima(str(datos_guia.get("documentos") or "").strip(), "documentos", 200)
    obs_ventas = longitud_maxima(str(datos_guia.get("obs_ventas") or "").strip(), "obs_ventas", 1000)

    envio_directo = _bool_flag(datos_guia.get("envio_directo_cedis"))

    entrega_nombre = longitud_maxima(
        str(datos_guia.get("entrega_nombre") or user.get("nombre") or "").strip(),
        "entrega_nombre", 120
    )

    # --- Campos de prellenado opcionales (CEDIS los verá auto-completados) ---
    def _t(campo: str, maxlen: int = 100) -> str:
        return longitud_maxima(str(datos_guia.get(campo) or "").strip(), campo, maxlen)

    def _int_nn(campo: str) -> int:
        try:
            val = int(datos_guia.get(campo) or 0)
        except (TypeError, ValueError):
            val = 0
        return max(0, val)

    pre = {
        "transportador_nombre": _t("transportador_nombre", 120),
        "transportador_cc":     _t("transportador_cc", 50),
        "transportador_tel":    _t("transportador_tel", 50),
        "transportador_vehiculo": _t("transportador_vehiculo", 80),
        "transportador_placa":  _t("transportador_placa", 20),
        "transportador_flete":  _t("transportador_flete", 40),
        "cliente_recibe_nombre": _t("cliente_recibe_nombre", 120),
        # Campos de bultos (ventas los informa, cedis confirma/edita)
        "cajas":   str(_int_nn("cajas")),
        "bolsas":  str(_int_nn("bolsas")),
        "cayvas":  str(_int_nn("cayvas")),
        "sobres":  str(_int_nn("sobres")),
        "otros":   _t("otros", 200),
        "totales": str(_int_nn("totales")),
    }

    ahora = ahora_txt()
    estado_inicial = "EN_CEDIS" if envio_directo else "CREADA"

    with get_db_lock():
        with db_connection(commit=True) as conn:
            consecutivo = int(get_config("siguiente", "1"))
            conn.execute(
                "UPDATE config SET valor = ? WHERE clave = 'siguiente'",
                (str(consecutivo + 1),),
            )
            cur = conn.execute(
                """
                INSERT INTO guias(consecutivo, cliente, ciudad, direccion, documentos,
                                  obs_ventas, envio_directo_cedis, creada_por, creada_en, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (consecutivo, cliente, ciudad, direccion, documentos, obs_ventas,
                 1 if envio_directo else 0,
                 user.get("id"), ahora, estado_inicial),
            )
            guia_id = cur.lastrowid

    datos_evento_creacion = {"entrega_nombre": entrega_nombre}
    datos_evento_creacion.update({k: v for k, v in pre.items() if v})

    agregar_evento(
        guia_id=guia_id,
        tipo="creacion",
        user=user,
        datos=datos_evento_creacion,
        dispositivo=dispositivo,
        ip=ip,
    )

    if envio_directo:
        agregar_evento(
            guia_id=guia_id,
            tipo="envio_directo_cedis",
            user=user,
            datos={
                "motivo": "Envío directo marcado por ventas (no requiere paso administrativo)",
            },
            dispositivo=dispositivo,
            ip=ip,
        )

    logger.info(
        "Guía creada id=%s consecutivo=%s usuario=%s envio_directo=%s",
        guia_id, consecutivo, user.get("usuario"), envio_directo,
    )
    return guia_id, consecutivo


def obtener_guia(guia_id: int) -> Optional[Dict[str, Any]]:
    with db_connection() as conn:
        fila = conn.execute("SELECT * FROM guias WHERE id = ?", (guia_id,)).fetchone()
        return dict(fila) if fila else None


def ver_evento(guia_id: int, tipo: str) -> Optional[Dict[str, Any]]:
    from guias_coodescor.services.eventos_service import obtener_evento_por_tipo
    return obtener_evento_por_tipo(guia_id, tipo)


def obtener_prellenado_ventas(guia_id: int) -> Dict[str, Any]:
    """Devuelve el dict de campos pre-llenados por ventas (transportador, cliente_recibe, bultos)."""
    ev = ver_evento(guia_id, "creacion")
    if not ev:
        return {}
    d = ev.get("datos") or {}
    def _num(k):
        try: return int(d.get(k) or 0)
        except (TypeError, ValueError): return 0
    return {
        "transportador_nombre":    d.get("transportador_nombre") or "",
        "transportador_cc":        d.get("transportador_cc") or "",
        "transportador_tel":       d.get("transportador_tel") or "",
        "transportador_vehiculo":  d.get("transportador_vehiculo") or "",
        "transportador_placa":     d.get("transportador_placa") or "",
        "transportador_flete":     d.get("transportador_flete") or "",
        "cliente_recibe_nombre":   d.get("cliente_recibe_nombre") or "",
        "cajas":   _num("cajas"),
        "bolsas":  _num("bolsas"),
        "cayvas":  _num("cayvas"),
        "sobres":  _num("sobres"),
        "otros":   d.get("otros") or "",
        "totales": _num("totales"),
    }


def buscar_guias(
    q: str = "",
    estado: str = "",
    limite: int = 200,
    solo_estado: Optional[str] = None,
) -> List[Dict[str, Any]]:
    q = (q or "").strip()
    estado = (estado or solo_estado or "").strip()
    estado = validar_estado_guia(estado) if estado else ""
    sql = "SELECT * FROM guias WHERE 1=1"
    args: List[Any] = []
    if q:
        sql += " AND (CAST(consecutivo AS TEXT) LIKE ? OR cliente LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if estado:
        sql += " AND estado = ?"
        args.append(estado)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(int(limite))
    with db_connection() as conn:
        filas = conn.execute(sql, args).fetchall()
        return [dict(r) for r in filas]


def listar_guias_por_estado(estado: str, limite: int = 10) -> List[Dict[str, Any]]:
    return buscar_guias(estado=estado, limite=limite)


def contar_por_estado() -> List[Dict[str, Any]]:
    with db_connection() as conn:
        filas = conn.execute(
            "SELECT estado, COUNT(*) n FROM guias GROUP BY estado"
        ).fetchall()
        return [{"estado": r["estado"], "n": r["n"]} for r in filas]


def validar_transicion(guia_id: int, tipo_evento: str, user: dict) -> Dict[str, Any]:
    """
    Verifica permisos y precondiciones para ejecutar un evento sobre una guía.
    Admite rol principal + roles adicionales por evento (PERMISO_ADICIONAL_ROL).
    Soporta comodines especiales en ESTADO_ESPERADO_POR_EVENTO:
      - __RECIBIDA_O_EN_CEDIS__: válido para control_cedis desde flujo normal o directo.
      - __EDITABLE__: guía aún NO procesada (solo estado CREADA o EN_CEDIS sin eventos posteriores).
    """
    rol_requerido = PERMISO.get(tipo_evento)
    if not rol_requerido:
        raise ValueError(f"Tipo de evento no reconocido: {tipo_evento}")

    roles_permitidos = [rol_requerido] + (PERMISO_ADICIONAL_ROL.get(tipo_evento) or [])
    rol_user = user.get("rol")
    if rol_user not in roles_permitidos:
        raise ForbiddenError(
            f"No tiene permisos para realizar la acción '{tipo_evento}'. "
            f"Roles permitidos: {', '.join(roles_permitidos)}"
        )

    guia = obtener_guia(guia_id)
    if not guia:
        raise GuiaNoExisteError("Guía no existe")

    esperado = ESTADO_ESPERADO_POR_EVENTO.get(tipo_evento)
    if esperado == "__RECIBIDA_O_EN_CEDIS__":
        if guia["estado"] not in ("RECIBIDA_ADMIN", "EN_CEDIS"):
            raise EstadoInvalidoError(
                f"No se puede aplicar '{tipo_evento}': estado actual '{guia['estado']}'. "
                f"Esperaba RECIBIDA_ADMIN o EN_CEDIS."
            )
    elif esperado == "__EN_RUTA_O_EN_CEDIS__":
        if guia["estado"] not in ("EN_RUTA", "EN_CEDIS"):
            raise EstadoInvalidoError(
                f"No se puede aplicar '{tipo_evento}': estado actual '{guia['estado']}'. "
                f"Esperaba EN_RUTA o EN_CEDIS."
            )
    elif esperado == "__EDITABLE__":
        from guias_coodescor.services.eventos_service import listar_eventos
        estados_protegidos = ("RECIBIDA_ADMIN", "EN_RUTA", "ENTREGADA", "ANULADA")
        if guia["estado"] in estados_protegidos:
            raise EstadoInvalidoError(
                f"La guía ya fue procesada (estado {guia['estado']}); no se puede editar. "
                f"Solo se permite edición antes de recepción/administrativa o control CEDIS."
            )
        evs = listar_eventos(guia_id)
        tipos_procesados = {e["tipo"] for e in evs if e["tipo"] not in ("creacion", "envio_directo_cedis")}
        if tipos_procesados:
            raise EstadoInvalidoError(
                f"Esta guía ya fue procesada por alguien más (eventos: {', '.join(sorted(tipos_procesados))}); "
                f"no se pueden modificar los datos para proteger la trazabilidad."
            )
    elif esperado is not None and guia["estado"] != esperado:
        raise EstadoInvalidoError(
            f"No se puede aplicar '{tipo_evento}': la guía ya está en estado '{guia['estado']}'."
            f" Se esperaba '{esperado}'."
        )
    return guia


def validar_datos_evento(
    tipo_evento: str,
    datos: Dict[str, Any],
    prellenado: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Valida los datos obligatorios para cada evento.
    Si 'prellenado' viene desde la creación de ventas, completa campos vacíos
    para que CEDIS no tenga que digitar lo que ya está registrado.
    """
    datos = dict(datos or {})
    prellenado = prellenado or {}

    def _text(campo, maxlen=200):
        val = datos.get(campo) or ""
        if not isinstance(val, str) or not val.strip():
            val = prellenado.get(campo) or ""
        return longitud_maxima(str(val).strip(), campo, maxlen)

    if tipo_evento in ("recepcion_admin",):
        datos["recibe"] = requerir(_text("recibe", 120), "recibe",
                                   "Indique el nombre de quien recibe en bodega")
    if tipo_evento == "entrega_cliente":
        nombre_recibe = _text("recibe", 120) or prellenado.get("cliente_recibe_nombre") or ""
        datos["recibe"] = requerir(
            longitud_maxima(nombre_recibe, "recibe", 120),
            "recibe",
            "Indique el nombre de quien recibe en la entrega final",
        )

    if tipo_evento in ("recepcion_admin", "control_cedis", "entrega_transporte"):
        firma = datos.get("firma") or ""
        if not isinstance(firma, str) or not firma.startswith("data:image"):
            raise ValidationError("Falta la firma requerida", "firma")

    if tipo_evento == "entrega_cliente":
        firma = datos.get("firma") or ""
        foto = datos.get("foto") or ""
        ok_firma = isinstance(firma, str) and firma.startswith("data:image")
        ok_foto = isinstance(foto, str) and foto.startswith("data:image")
        if not ok_firma and not ok_foto:
            raise ValidationError(
                "Se requiere firma o foto del cliente para cerrar la entrega",
                "entrega_cliente",
            )
        datos["obs"] = _text("obs", 1000)

    if tipo_evento == "anular":
        datos["motivo"] = requerir(_text("motivo", 500), "motivo",
                                   "Indique el motivo de la anulación")

    if tipo_evento == "control_cedis":
        for c in ("cajas", "bolsas", "cayvas", "sobres", "totales"):
            raw = datos.get(c)
            # Si no lo llenaron o es 0, usar el prellenado de ventas
            if raw in (None, "", "0", 0):
                raw = prellenado.get(c) or 0
            try:
                datos[c] = int(raw)
            except (TypeError, ValueError):
                raise ValidationError(f"{c} debe ser un número entero", c)
            if datos[c] < 0:
                raise ValidationError(f"{c} no puede ser negativo", c)
        datos["obs"] = _text("obs", 1000)
        otros_raw = datos.get("otros") or ""
        if not isinstance(otros_raw, str) or not otros_raw.strip():
            otros_raw = prellenado.get("otros") or ""
        datos["otros"] = longitud_maxima(str(otros_raw).strip(), "otros", 200)
        datos["scan"] = _text("scan", 200)
        vc = (datos.get("vehiculo_cumple") or "").lower()
        datos["vehiculo_cumple"] = "si" if vc == "si" else "no"

    if tipo_evento == "entrega_transporte":
        nombre_t = _text("nombre", 120) or prellenado.get("transportador_nombre") or ""
        datos["nombre"] = requerir(
            longitud_maxima(nombre_t, "nombre", 120),
            "nombre",
            "Indique el nombre del transportador",
        )
        mapeo = {
            "cc": "transportador_cc",
            "tel": "transportador_tel",
            "vehiculo": "transportador_vehiculo",
            "placa": "transportador_placa",
            "flete": "transportador_flete",
        }
        for campo_destino, campo_pre in mapeo.items():
            val = datos.get(campo_destino) or ""
            if not isinstance(val, str) or not val.strip():
                val = prellenado.get(campo_pre) or ""
            datos[campo_destino] = longitud_maxima(str(val).strip(), campo_destino, 80)

    return datos


def procesar_evento(
    guia_id: int,
    tipo_evento: str,
    user: dict,
    datos: Dict[str, Any],
    dispositivo: Optional[str] = None,
    ip: Optional[str] = None,
) -> int:
    validar_transicion(guia_id, tipo_evento, user)
    pre = obtener_prellenado_ventas(guia_id)
    datos_ok = validar_datos_evento(tipo_evento, datos, prellenado=pre)
    evento_id = agregar_evento(guia_id, tipo_evento, user, datos_ok, dispositivo, ip)
    estado_siguiente = TRANSICION.get(tipo_evento)
    if estado_siguiente is not None:
        with db_connection(commit=True) as conn:
            conn.execute(
                "UPDATE guias SET estado = ? WHERE id = ?",
                (estado_siguiente, guia_id),
            )
    # edicion_guia requiere actualizar columnas de la guía directamente
    if tipo_evento == "edicion_guia":
        _aplicar_cambios_edicion(guia_id, datos_ok)
    return evento_id


def _aplicar_cambios_edicion(guia_id: int, datos_ok: Dict[str, Any]) -> None:
    """Escribe los campos editados sobre la tabla guias y actualiza el evento creacion para reflejar los prellenados."""
    campos_guia = {}
    for col in ("cliente", "ciudad", "direccion", "documentos", "obs_ventas"):
        if col in datos_ok and datos_ok[col] is not None:
            campos_guia[col] = str(datos_ok[col]).strip()
    if "envio_directo_cedis" in datos_ok:
        campos_guia["envio_directo_cedis"] = 1 if _bool_flag(datos_ok["envio_directo_cedis"]) else 0
    if campos_guia:
        sets = ", ".join(f"{k} = ?" for k in campos_guia.keys())
        vals = list(campos_guia.values()) + [guia_id]
        with db_connection(commit=True) as conn:
            conn.execute(f"UPDATE guias SET {sets} WHERE id = ?", vals)
    # Actualizar evento creacion con los nuevos prellenados (para que CEDIS los vea al autocompletar)
    ev = ver_evento(guia_id, "creacion")
    if ev:
        d_ant = dict(ev.get("datos") or {})
        for k in ("entrega_nombre", "transportador_nombre", "transportador_cc",
                  "transportador_tel", "transportador_vehiculo", "transportador_placa",
                  "transportador_flete", "cliente_recibe_nombre"):
            if k in datos_ok and datos_ok[k] not in (None, ""):
                d_ant[k] = str(datos_ok[k])
        for k in ("cajas", "bolsas", "cayvas", "sobres", "totales"):
            if k in datos_ok:
                try:
                    d_ant[k] = str(int(datos_ok[k]))
                except (TypeError, ValueError):
                    pass
        if "otros" in datos_ok:
            d_ant["otros"] = str(datos_ok["otros"] or "")
        import json
        from guias_coodescor.database.connection import db_connection as _dbc
        with _dbc(commit=True) as conn:
            conn.execute(
                "UPDATE eventos SET datos = ? WHERE id = ?",
                (json.dumps(d_ant, ensure_ascii=False), ev["id"]),
            )


def editar_guia(
    guia_id: int,
    user: dict,
    datos_nuevos: Dict[str, Any],
    dispositivo: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Permite a Ventas (o Admin del sistema) corregir datos de la guía ANTES de que
    otro rol la procese.
    1) Valida que la guía siga siendo editable.
    2) Compara cambios vs la creación.
    3) Registra un evento AUDITORÍA 'edicion_guia' con:
         - campos_anteriores, campos_nuevos, diff
    4) Aplica los cambios a la tabla guias y a los prellenados del evento creacion.
    Devuelve (evento_id, diff_generado).
    """
    validar_transicion(guia_id, "edicion_guia", user)
    actual = obtener_guia(guia_id)
    pre_actual = obtener_prellenado_ventas(guia_id)

    def _s(v):
        return "" if v is None else str(v).strip()

    def _i(v, d=0):
        try: return int(v or d)
        except (TypeError, ValueError): return d

    # Normalizar datos_nuevos
    dn = {
        "cliente": longitud_maxima(_s(datos_nuevos.get("cliente")) or actual.get("cliente") or "", "cliente", 200),
        "ciudad": longitud_maxima(_s(datos_nuevos.get("ciudad")) or actual.get("ciudad") or "", "ciudad", 120),
        "direccion": longitud_maxima(_s(datos_nuevos.get("direccion")) or actual.get("direccion") or "", "direccion", 300),
        "documentos": longitud_maxima(_s(datos_nuevos.get("documentos")) or actual.get("documentos") or "", "documentos", 200),
        "obs_ventas": longitud_maxima(_s(datos_nuevos.get("obs_ventas")) or actual.get("obs_ventas") or "", "obs_ventas", 1000),
        "entrega_nombre": longitud_maxima(_s(datos_nuevos.get("entrega_nombre")) or pre_actual.get("entrega_nombre") or user.get("nombre") or "", "entrega_nombre", 120),
        "transportador_nombre": longitud_maxima(_s(datos_nuevos.get("transportador_nombre")) or pre_actual.get("transportador_nombre") or "", "transportador_nombre", 120),
        "transportador_cc": longitud_maxima(_s(datos_nuevos.get("transportador_cc")) or pre_actual.get("transportador_cc") or "", "transportador_cc", 50),
        "transportador_tel": longitud_maxima(_s(datos_nuevos.get("transportador_tel")) or pre_actual.get("transportador_tel") or "", "transportador_tel", 50),
        "transportador_vehiculo": longitud_maxima(_s(datos_nuevos.get("transportador_vehiculo")) or pre_actual.get("transportador_vehiculo") or "", "transportador_vehiculo", 80),
        "transportador_placa": longitud_maxima(_s(datos_nuevos.get("transportador_placa")) or pre_actual.get("transportador_placa") or "", "transportador_placa", 20),
        "transportador_flete": longitud_maxima(_s(datos_nuevos.get("transportador_flete")) or pre_actual.get("transportador_flete") or "", "transportador_flete", 40),
        "cliente_recibe_nombre": longitud_maxima(_s(datos_nuevos.get("cliente_recibe_nombre")) or pre_actual.get("cliente_recibe_nombre") or "", "cliente_recibe_nombre", 120),
        "otros": longitud_maxima(_s(datos_nuevos.get("otros")) or pre_actual.get("otros") or "", "otros", 200),
        "cajas":   _i(datos_nuevos.get("cajas"),   pre_actual.get("cajas") or 0),
        "bolsas":  _i(datos_nuevos.get("bolsas"),  pre_actual.get("bolsas") or 0),
        "cayvas":  _i(datos_nuevos.get("cayvas"),  pre_actual.get("cayvas") or 0),
        "sobres":  _i(datos_nuevos.get("sobres"),  pre_actual.get("sobres") or 0),
        "totales": _i(datos_nuevos.get("totales"), pre_actual.get("totales") or 0),
        "envio_directo_cedis": _bool_flag(datos_nuevos.get("envio_directo_cedis", actual.get("envio_directo_cedis"))),
    }
    requerir(dn["cliente"], "cliente")
    requerir(dn["ciudad"], "ciudad")

    # Calcular diff (anterior vs nuevo)
    base_ant = {
        "cliente": actual.get("cliente", ""),
        "ciudad": actual.get("ciudad", ""),
        "direccion": actual.get("direccion", ""),
        "documentos": actual.get("documentos", ""),
        "obs_ventas": actual.get("obs_ventas", ""),
        "envio_directo_cedis": bool(actual.get("envio_directo_cedis")),
        "entrega_nombre": pre_actual.get("entrega_nombre", ""),
        "transportador_nombre": pre_actual.get("transportador_nombre", ""),
        "transportador_cc": pre_actual.get("transportador_cc", ""),
        "transportador_tel": pre_actual.get("transportador_tel", ""),
        "transportador_vehiculo": pre_actual.get("transportador_vehiculo", ""),
        "transportador_placa": pre_actual.get("transportador_placa", ""),
        "transportador_flete": pre_actual.get("transportador_flete", ""),
        "cliente_recibe_nombre": pre_actual.get("cliente_recibe_nombre", ""),
        "cajas": pre_actual.get("cajas", 0),
        "bolsas": pre_actual.get("bolsas", 0),
        "cayvas": pre_actual.get("cayvas", 0),
        "sobres": pre_actual.get("sobres", 0),
        "otros": pre_actual.get("otros", ""),
        "totales": pre_actual.get("totales", 0),
    }
    base_nueva = {
        "cliente": dn["cliente"],
        "ciudad": dn["ciudad"],
        "direccion": dn["direccion"],
        "documentos": dn["documentos"],
        "obs_ventas": dn["obs_ventas"],
        "envio_directo_cedis": bool(dn["envio_directo_cedis"]),
        "entrega_nombre": dn["entrega_nombre"],
        "transportador_nombre": dn["transportador_nombre"],
        "transportador_cc": dn["transportador_cc"],
        "transportador_tel": dn["transportador_tel"],
        "transportador_vehiculo": dn["transportador_vehiculo"],
        "transportador_placa": dn["transportador_placa"],
        "transportador_flete": dn["transportador_flete"],
        "cliente_recibe_nombre": dn["cliente_recibe_nombre"],
        "cajas": dn["cajas"],
        "bolsas": dn["bolsas"],
        "cayvas": dn["cayvas"],
        "sobres": dn["sobres"],
        "otros": dn["otros"],
        "totales": dn["totales"],
    }
    diff = {}
    for k in base_ant.keys():
        ant = base_ant[k]
        nue = base_nueva[k]
        if str(ant) != str(nue):
            diff[k] = {"anterior": ant, "nuevo": nue}

    # Si no hay diferencias, devolvemos sin registrar evento (no ha cambiado nada)
    if not diff:
        return 0, {}

    # Cambio de envio directo: actualizar el estado de la guía y registrar evento correspondiente
    cambio_envio_directo = dn["envio_directo_cedis"] != bool(actual.get("envio_directo_cedis"))
    nuevo_estado = None
    if cambio_envio_directo:
        if dn["envio_directo_cedis"] and actual.get("estado") == "CREADA":
            nuevo_estado = "EN_CEDIS"
        elif not dn["envio_directo_cedis"] and actual.get("estado") == "EN_CEDIS":
            # Si aún NO se ejecutó control_cedis (ya lo valida editable), revertimos
            nuevo_estado = "CREADA"

    if nuevo_estado:
        with db_connection(commit=True) as conn:
            conn.execute(
                "UPDATE guias SET estado = ?, envio_directo_cedis = ? WHERE id = ?",
                (nuevo_estado, 1 if dn["envio_directo_cedis"] else 0, guia_id),
            )
        tipo_extra = "envio_directo_cedis" if nuevo_estado == "EN_CEDIS" else None
        if tipo_extra:
            agregar_evento(
                guia_id=guia_id, tipo=tipo_extra, user=user,
                datos={"motivo": "Cambiado al editar la guía desde Ventas"},
                dispositivo=dispositivo, ip=ip,
            )

    # Aplicar los cambios de campos (columnas guía + evento creacion)
    _aplicar_cambios_edicion(guia_id, dn)

    # Registrar evento de auditoría edicion_guia
    datos_auditoria = {
        "campos_modificados": list(diff.keys()),
        "detalle_cambios": diff,
        "resumen": f"Se modificaron {len(diff)} campos",
    }
    evento_id = agregar_evento(
        guia_id=guia_id, tipo="edicion_guia", user=user,
        datos=datos_auditoria, dispositivo=dispositivo, ip=ip,
    )
    logger.info(
        "Edición guía id=%s usuario=%s campos=%s",
        guia_id, user.get("usuario"), ",".join(diff.keys()),
    )
    return evento_id, diff


def generar_codigo_verificacion(g: Dict[str, Any]) -> str:
    return codigo_verificacion(int(g["id"]), int(g["consecutivo"]))


def estado_info(estado: str) -> Tuple[str, str]:
    return ESTADOS.get(estado, (estado, "#666"))
