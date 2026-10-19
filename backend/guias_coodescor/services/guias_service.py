#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio de negocio para guías: CRUD, búsqueda, validación de transiciones
de estado y permisos.
"""
from typing import Any, Dict, List, Optional, Tuple
import json, re

from guias_coodescor.config import (
    ESTADO_ESPERADO_POR_EVENTO,
    ESTADOS,
    PERMISO,
    PERMISO_ADICIONAL_ROL,
    ROLES_VALIDOS,
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
    nit = longitud_maxima(str(datos_guia.get("nit") or "").strip(), "nit", 60)
    centro_operacion = (str(datos_guia.get("centro_operacion") or "") or "-").strip()
    if centro_operacion == "" or centro_operacion == "—":
        centro_operacion = "-"
    centro_operacion = longitud_maxima(centro_operacion, "centro_operacion", 20)
    prefijo = (str(datos_guia.get("prefijo") or "") or "FV").strip().upper()
    if prefijo not in ("FV", "TB", "PD", "TR"):
        prefijo = "FV"
    prefijo = longitud_maxima(prefijo, "prefijo", 5)

    # --- Multi-documentos: si viene JSON array [{prefijo,numero}], validar,
    #     forzar no-duplicados, re-escribir prefijo (primero) y documentos string legacy.
    PREFIJOS_VALIDOS = {"FV", "TB", "PD", "TR"}
    docs_json_raw = datos_guia.get("documentos_json") if isinstance(datos_guia, dict) else None
    if isinstance(docs_json_raw, str) and docs_json_raw.strip():
        try:
            docs_parsed = json.loads(docs_json_raw)
        except (ValueError, TypeError):
            raise ValidationError("El JSON de documentos no es válido (multi-documentos corrupto).")
        if not isinstance(docs_parsed, list) or not docs_parsed:
            raise ValidationError("Debes incluir al menos un documento (prefijo + número).")
        if len(docs_parsed) > 50:
            raise ValidationError("Máximo 50 documentos por guía.")
        _claves = set()
        _items_ok = []
        _num_err = 0
        for it in docs_parsed:
            if not isinstance(it, dict):
                raise ValidationError("Formato inválido en fila de documentos.")
            p = (str(it.get("prefijo") or "").strip() or "").upper()
            n = str(it.get("numero") or "").strip()
            if not p or not n:
                _num_err += 1
                continue
            if p not in PREFIJOS_VALIDOS:
                raise ValidationError(f"Prefijo inválido '{p}' en uno de los documentos (permitidos: FV/TB/PD/TR).")
            _n_norm = re.sub(r"[\s\-_/().]+", "", n.upper())
            if not _n_norm:
                _num_err += 1
                continue
            clave = f"{p}|{_n_norm}"
            if clave in _claves:
                raise ValidationError(f"Documento duplicado detectado: {p} {n}. Verifica los números.")
            _claves.add(clave)
            _items_ok.append({"prefijo": p, "numero": n})
        if _num_err > 0:
            raise ValidationError(f"{_num_err} fila(s) de documentos tienen número vacío o inválido.")
        if not _items_ok:
            raise ValidationError("Ningún documento válido. Ingresa al menos un número.")
        prefijo = _items_ok[0]["prefijo"]
        prefijo = prefijo if prefijo in PREFIJOS_VALIDOS else "FV"
        prefijo = longitud_maxima(prefijo, "prefijo", 5)
        documentos = " - ".join(f"{r['prefijo']} {r['numero']}" for r in _items_ok)
        documentos = longitud_maxima(documentos, "documentos", 1000)
        # --- Guardar JSON serializado compacto en metadata
        _extra_metadata_docs = {"docs": _items_ok}
    else:
        _extra_metadata_docs = None
    generar_link_recibido = _bool_flag(datos_guia.get("generar_link_recibido")) or _bool_flag(datos_guia.get("generar_link_entrega"))

    try:
        try:
            from guias_coodescor.services.clientes_service import asegurar_cliente_desde_ventas as _fn_ac
        except Exception:
            import importlib as _imp
            _m = _imp.import_module("clientes_service", package="guias_coodescor.services")
            _fn_ac = getattr(_m, "asegurar_cliente_desde_ventas")
        _fn_ac(
            nit=nit,
            razon_social=cliente,
            direccion=direccion,
            ciudad=ciudad,
            telefono=str(datos_guia.get("telefono") or "").strip() or None,
            email=str(datos_guia.get("email") or "").strip() or None,
        )
    except Exception as _e_cliente:
        logger.warning(
            "No se pudo asegurar cliente NIT=%s (no bloquea crear guía): %s",
            (nit or "VACIO"), _e_cliente,
        )

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

    cajas  = _int_nn("cajas")
    bolsas = _int_nn("bolsas")
    cayvas = _int_nn("cayvas")
    sobres = _int_nn("sobres")
    totales_auto = cajas + bolsas + cayvas + sobres
    pre = {
        "transportador_nombre": _t("transportador_nombre", 120),
        "transportador_cc":     _t("transportador_cc", 50),
        "transportador_tel":    _t("transportador_tel", 50),
        "transportador_vehiculo": _t("transportador_vehiculo", 80),
        "transportador_placa":  _t("transportador_placa", 20),
        "transportador_flete":  _t("transportador_flete", 40),
        "cliente_recibe_nombre": _t("cliente_recibe_nombre", 120),
        # Campos de bultos (ventas los informa, cedis confirma/edita)
        # TOTAL se calcula automáticamente como suma (no depende de input usuario)
        "cajas":   str(cajas),
        "bolsas":  str(bolsas),
        "cayvas":  str(cayvas),
        "sobres":  str(sobres),
        "otros":   _t("otros", 200),
        "totales": str(totales_auto),
    }
    logger.debug(
        "crear_guia calcula totales=%d (cajas=%d bolsas=%d cavas=%d sobres=%d)",
        totales_auto, cajas, bolsas, cayvas, sobres,
    )

    ahora = ahora_txt()
    estado_inicial = "EN_CEDIS" if envio_directo else "CREADA"

    with get_db_lock():
        with db_connection(commit=True) as conn:
            consecutivo = int(get_config("siguiente", "1"))
            conn.execute(
                "UPDATE config SET valor = ? WHERE clave = 'siguiente'",
                (str(consecutivo + 1),),
            )
            cols_actuales = {str(r[1] or "") for r in conn.execute("PRAGMA table_info(guias)").fetchall()}
            col_val = [
                ("consecutivo", consecutivo),
                ("cliente", cliente),
                ("ciudad", ciudad),
                ("direccion", direccion),
                ("documentos", documentos),
                ("obs_ventas", obs_ventas),
                ("envio_directo_cedis", 1 if envio_directo else 0),
                ("creada_por", user.get("id")),
                ("creada_en", ahora),
                ("estado", estado_inicial),
                ("nit", nit or None),
                ("centro_operacion", centro_operacion or None),
                ("prefijo", prefijo or None),
            ]
            cols_presentes = [c for c, _ in col_val if c in cols_actuales]
            vals_presentes = [v for c, v in col_val if c in cols_actuales]
            placeholders = ",".join(["?"] * len(cols_presentes))
            sql = f'INSERT INTO guias({", ".join(cols_presentes)}) VALUES ({placeholders})'
            cur = conn.execute(sql, tuple(vals_presentes))
            guia_id = cur.lastrowid

    datos_evento_creacion = {"entrega_nombre": entrega_nombre}
    datos_evento_creacion.update({k: v for k, v in pre.items() if v})
    datos_evento_creacion["nit"] = nit
    datos_evento_creacion["centro_operacion"] = centro_operacion
    datos_evento_creacion["prefijo"] = prefijo
    if generar_link_recibido:
        datos_evento_creacion["generar_link_recibido"] = True
    else:
        datos_evento_creacion["generar_link_recibido"] = False

    agregar_evento(
        guia_id=guia_id,
        tipo="creacion",
        user=user,
        datos=datos_evento_creacion,
        dispositivo=dispositivo,
        ip=ip,
    )

    if generar_link_recibido:
        try:
            from guias_coodescor.services.tokens_service import generar_token_entrega as _gte_vta
            _gte_vta(guia_id=guia_id, user=user, regenerar_si_existe=False)
            logger.info(
                "Guía %s: Link de recibido generado INMEDIATAMENTE por Ventas (checkbox).",
                guia_id,
            )
        except Exception as _e_link:
            logger.warning(
                "Guía %s: No se pudo generar link de recibido en crear_guia: %s",
                guia_id, _e_link, exc_info=True,
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
    """Devuelve el dict de campos pre-llenados por ventas, transportador y ediciones.
    FIX BUG #5 (25/09/2026): ANTES esta función SÓLO miraba el evento "creacion".
    El PROBLEMA era que el ADMINISTRATIVO guarda los datos del transportador
    EXTERNO (nombre / placa / firma transportador) en eventos "edicion_guia"
    POSTERIORES a la creación → obtener_prellenado_ventas() devolvía cadena vacía
    para todos esos campos, y la vista DETALLE de la guía (/guias/<id>) pintaba:
        "Firma: —" y "Firma (capturada por Administrativo): ."
    SOLUCIÓN: Hacemos MERGE (último valor gana) de:
        1) evento "creacion" primero (base)
        2) TODOS los eventos "asignacion_transportador" (ordenado por creado_en ASC, último gana)
        3) TODOS los eventos "edicion_guia" (ordenado ASC; último valor de cada key gana)
        4) TODOS los eventos "recepcion_admin" (por si guarda info adicional)
    De esta forma CUALQUIER campo que el Administrativo/CEDIS actualice a través
    de eventos (no solo creacion) SE VE INMEDIATAMENTE reflejado en la vista
    detalle guía y en los formularios pre-llenados.
    """
    from guias_coodescor.services.eventos_service import listar_eventos as _le_full
    todos = sorted(
        _le_full(guia_id) or [],
        key=lambda e: str(e.get("creado_en") or "") or str(e.get("id") or 0),
    )
    if not todos:
        return {}
    merged: Dict[str, Any] = {}
    for ev in todos:
        tipo = str(ev.get("tipo") or "")
        if tipo not in ("creacion", "edicion_guia", "asignacion_transportador", "recepcion_admin"):
            continue
        d = ev.get("datos") or {}
        if isinstance(d, dict):
            # Merge plano (último valor gana): sobreescribimos cada key con el valor nuevo
            for k, v in d.items():
                if v is None:
                    # No sobreescribir valores buenos con None
                    continue
                if isinstance(v, str) and v == "" and k in merged:
                    # No sobreescribir valor NO vacío con vacío (protección)
                    continue
                merged[k] = v
    # Campos prellenados transportador (fuerzan strings vacíos como default, no None)
    def _s(k):
        v = merged.get(k)
        return "" if v is None else str(v)
    def _num(k):
        v = merged.get(k)
        if v in (None, "", "0", 0):
            return 0
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            # Si es float (ej 12.0), truncar
            try: return max(0, int(float(v)))
            except (TypeError, ValueError): return 0
    return {
        # --- Datos transportador (vienen de edicion_guia al guardar Administrativo Proceso Unif) ---
        "transportador_nombre":    _s("transportador_nombre"),
        "transportador_cc":        _s("transportador_cc"),
        "transportador_tel":       _s("transportador_tel"),
        "transportador_vehiculo":  _s("transportador_vehiculo"),
        "transportador_placa":     _s("transportador_placa"),
        "transportador_flete":     _s("transportador_flete"),
        # --- Firma del transportador capturada por Administrativo (EXTERNO) ---
        #   Key que guarda Paso C Proceso Admin Unificado en evento edicion_guia:
        "transportador_firma_admin": _s("transportador_firma_admin"),
        # --- Datos persona que retira en CEDIS (envío directo / cliente que recoge) ---
        "cliente_recibe_nombre":   _s("cliente_recibe_nombre"),
        # --- Campos nuevos Ventas 2026 (nit/centro/prefijo/generar_link_recibido) ---
        "nit":                     _s("nit"),
        "centro_operacion":        _s("centro_operacion"),
        "prefijo":                 _s("prefijo"),
        "generar_link_recibido":   bool(merged.get("generar_link_recibido")),
        # --- Bultos (totales cajas/bolsas/cayvas/sobres/otros/totales) ---
        "cajas":   _num("cajas"),
        "bolsas":  _num("bolsas"),
        "cayvas":  _num("cayvas"),
        "sobres":  _num("sobres"),
        "otros":   _s("otros"),
        "totales": _num("totales"),
    }


def buscar_guias(
    q: str = "",
    estado: str = "",
    limite: int = 200,
    solo_estado: Optional[str] = None,
    transportador_asignado_id: Optional[int] = None,
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
    if transportador_asignado_id is not None:
        sql += " AND transportador_asignado_id = ?"
        args.append(int(transportador_asignado_id))
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
        rol_user = user.get("rol") or ""
        estados_protegidos = ("EN_RUTA", "ENTREGADA", "ANULADA")
        if guia["estado"] in estados_protegidos:
            raise EstadoInvalidoError(
                f"La guía ya fue procesada (estado {guia['estado']}); no se puede editar. "
                f"Solo se permite edición antes de que la mercancía salga a ruta."
            )
        evs = listar_eventos(guia_id)
        eventos_irreversibles = {"entrega_transporte", "entrega_cliente", "anular"}
        tipos_procesados = {e["tipo"] for e in evs if e.get("tipo") in eventos_irreversibles}
        if tipos_procesados:
            raise EstadoInvalidoError(
                f"Esta guía ya fue cerrada (eventos: {', '.join(sorted(tipos_procesados))}); "
                f"no se pueden modificar los datos para proteger la trazabilidad."
            )
        tiene_entrega_transporte = any(e.get("tipo") == "entrega_transporte" for e in evs)
        tiene_envio_directo_entregado = bool(guia.get("envio_directo_cedis")) and guia["estado"] == "ENTREGADA"
        if rol_user != "admin":
            if rol_user == "ventas":
                if guia["estado"] != "CREADA":
                    raise EstadoInvalidoError(
                        "Ventas solo puede editar guías en estado CREADA "
                        "(antes del proceso Administrativo)."
                    )
            elif rol_user == "administrativo":
                if tiene_entrega_transporte or guia["estado"] in ("EN_RUTA", "ENTREGADA", "ANULADA"):
                    raise EstadoInvalidoError(
                        "Administrativo no puede editar esta guía: ya tiene procesos de CEDIS finalizados."
                    )
            elif rol_user == "cedis":
                if tiene_entrega_transporte or guia["estado"] in ("EN_RUTA", "ENTREGADA", "ANULADA") or tiene_envio_directo_entregado:
                    raise EstadoInvalidoError(
                        "CEDIS no puede editar esta guía: ya procesó la entrega o está cerrada."
                    )
    elif esperado is not None and guia["estado"] != esperado:
        raise EstadoInvalidoError(
            f"No se puede aplicar '{tipo_evento}': la guía ya está en estado '{guia['estado']}'."
            f" Se esperaba '{esperado}'."
        )
    return guia


def proceso_unificado_administrativo(
    guia_id: int,
    user: dict,
    datos: Dict[str, Any],
    dispositivo: str = "web",
    ip: str = "-",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Proceso ÚNICO Administrativo en 1 click: recepción + asignar tipo + (si EXTERNO: datos + firma)

    Reglas de negocio (spec v1.0):
    - SÓLO ejecutan rol: administrativo o admin.
    - Guía DEBE estar en estado CREADA (solo procesa guías nuevas sin procesos).
    - Al finalizar: estado pasa a RECIBIDA_ADMIN y lista para CEDIS.
    - No se ejecuta en 2+ botones separados; TODO en una sola transacción.

    Devuelve (ok, mensaje, datos_extra)
    """
    from guias_coodescor.config import PERMISO_ASIGNAR_TIPO_TRANSPORTADOR
    roles_lista = sorted(list(PERMISO_ASIGNAR_TIPO_TRANSPORTADOR))
    requerir_rol(user, *roles_lista)
    datos = datos or {}

    g = obtener_guia(guia_id)
    if not g:
        raise GuiaNoExisteError(f"Guía {guia_id} no existe")
    if g.get("estado") != "CREADA":
        raise EstadoInvalidoError(
            f"Proceso Administrativo sólo puede ejecutarse sobre guías en estado CREADA. "
            f"Estado actual: {g.get('estado') or '-'}. Esta guía ya fue procesada por Administrativo."
        )

    def _s(v):
        return "" if v is None else str(v).strip()

    # --- Paso 1: Tipo transportador (OBLIGATORIO) ---
    tipo_t = (_s(datos.get("tipo_transportador")) or "").lower()
    if tipo_t not in ("propio", "externo"):
        raise ValidationError("Seleccione tipo de transportador PROPIO o EXTERNO")

    # --- Paso 2: Si PROPIO: transportador asignado ---
    transportador_asignado_id = None
    if tipo_t == "propio":
        tid_raw = datos.get("transportador_asignado_id")
        try:
            transportador_asignado_id = int(tid_raw or 0)
        except (TypeError, ValueError):
            transportador_asignado_id = 0
        if transportador_asignado_id <= 0:
            raise ValidationError("Seleccione un transportador propio de la lista")
        # Validar que exista y sea rol transportador activo
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id, rol, activo FROM usuarios WHERE id = ?",
                (transportador_asignado_id,),
            ).fetchone()
            if not row:
                raise ValidationError("El usuario transportador no existe")
            if str(row["rol"]) != "transportador" or int(row["activo"]) != 1:
                raise ValidationError("Transportador seleccionado no activo")

    # --- Paso 3: Si EXTERNO: datos + firma transportador externo ---
    ext_ok = {}
    if tipo_t == "externo":
        tn = _s(datos.get("transportador_nombre"))
        tcc = _s(datos.get("transportador_cc"))
        ttel = _s(datos.get("transportador_tel"))
        tveh = _s(datos.get("transportador_vehiculo"))
        tpla = _s(datos.get("transportador_placa"))
        tfl = _s(datos.get("transportador_flete"))
        requerir(tn, "transportador_nombre", "Nombre del transportador externo")
        requerir(tcc, "transportador_cc", "Documento transportador externo")
        requerir(ttel, "transportador_tel", "Teléfono transportador externo")
        requerir(tveh, "transportador_vehiculo", "Vehículo transportador externo")
        requerir(tpla, "transportador_placa", "Placa transportador externo")
        ext_ok = {
            "transportador_nombre": longitud_maxima(tn, "transportador_nombre", 120),
            "transportador_cc": longitud_maxima(tcc, "transportador_cc", 50),
            "transportador_tel": longitud_maxima(ttel, "transportador_tel", 50),
            "transportador_vehiculo": longitud_maxima(tveh, "transportador_vehiculo", 80),
            "transportador_placa": longitud_maxima(tpla, "transportador_placa", 20),
            "transportador_flete": longitud_maxima(tfl, "transportador_flete", 40),
        }
        # Firma transportador externo (OBLIGATORIA para EXTERNO en Administrativo)
        firma_ext = _s(datos.get("firma_transportador") or "")
        if firma_ext.startswith("data:image/") and "," in firma_ext and len(firma_ext) >= 80:
            ext_ok["transportador_firma_admin"] = firma_ext
        else:
            raise ValidationError("Falta la firma del transportador externo")

    # --- Paso 4: Recepción Administrativa (nombre quien recibe en Administrativo) ---
    recibe_nombre = (_s(datos.get("recibe")) or "").strip() or _s(user.get("nombre")) or _s(user.get("usuario"))

    # --- Unificación lectura firma recepción (backward compat 3 nombres):
    #   1) firma_recibido = nombre oficial nuevo (HTML canvas data-name="firma_recibido")
    #   2) firma_admin    = legacy (antes L77 usaba este nombre, por si habia datos
    #      en cache o formularios antiguos)
    #   3) firma          = nombre clave que validar_datos_evento requiere directamente
    #                        (por si algún endpoint lo usa)
    firma_candidatos = [
        _s(datos.get("firma_recibido") or ""),
        _s(datos.get("firma_admin") or ""),
        _s(datos.get("firma") or ""),
    ]
    firma_recibido_ok = ""
    for fc in firma_candidatos:
        if fc.startswith("data:image/") and "," in fc and len(fc) >= 80:
            firma_recibido_ok = fc
            break

    if not firma_recibido_ok:
        raise ValidationError(
            "Falta la FIRMA DE RECEPCIÓN ADMINISTRATIVA. "
            "Dibuja la firma en el recuadro (1er canvas, arriba del tipo de transportador)."
        )

    # --- INICIO TRANSACCIÓN ---
    # Paso A: recepcion_admin automático
    datos_rec = {"recibe": longitud_maxima(str(recibe_nombre), "recibe", 120)}
    # GUARDAR DOBLE CLAVE:
    #   - 'firma'           = OBLIGATORIA (lo requiere validar_datos_evento L779)
    #   - 'firma_recibido'  = Para auditoría / mostrar en vista luego
    datos_rec["firma"] = firma_recibido_ok
    datos_rec["firma_recibido"] = firma_recibido_ok
    procesar_evento(
        guia_id=guia_id,
        tipo_evento="recepcion_admin",
        user=user,
        datos=datos_rec,
        dispositivo=dispositivo,
        ip=ip,
    )

    # Paso B: asignar tipo transportador (actualiza campos guías)
    asignar_tipo_transportador(
        guia_id=guia_id,
        user=user,
        tipo=tipo_t,
        transportador_asignado_id=transportador_asignado_id,
    )

    # Paso C: si EXTERNO guardar datos + firma
    ext_con_firma = False
    if tipo_t == "externo":
        # ---- FIX BUG #5 ----
        # ANTES: se guardaba EN 2 EVENTOS separados (L489 datos, L503 firma).
        # RIESGO: si fallaba la 2da transacción, quedaba datos sin firma y
        # obtener_prellenado_ventas no mergeaba porque no estaban en mismo dict.
        # AHORA: guardar DATOS + FIRMA JUNTOS en UN SOLO EVENTO "edicion_guia"
        # (todos los campos y firma en el mismo dict datos).
        ext_unificado: Dict[str, Any] = {
            "transportador_nombre": longitud_maxima(tn, "transportador_nombre", 120),
            "transportador_cc": longitud_maxima(tcc, "transportador_cc", 50),
            "transportador_tel": longitud_maxima(ttel, "transportador_tel", 50),
            "transportador_vehiculo": longitud_maxima(tveh, "transportador_vehiculo", 80),
            "transportador_placa": longitud_maxima(tpla, "transportador_placa", 20),
            "transportador_flete": longitud_maxima(tfl, "transportador_flete", 40),
        }
        ext_firma = ext_ok.get("transportador_firma_admin") or ""
        if ext_firma:
            ext_unificado["transportador_firma_admin"] = ext_firma
            ext_unificado["motivo"] = (
                "Registro datos transportador EXTERNO + firma del transportador capturada en Bodega/Administrativa (Proceso Unificado)"
            )
            ext_con_firma = True
        else:
            ext_unificado["motivo"] = (
                "Registro datos transportador EXTERNO (Proceso Unificado Administrativo)"
            )
        # ---- UN SOLO procesar_evento ----
        procesar_evento(
            guia_id=guia_id,
            tipo_evento="edicion_guia",
            user=user,
            datos=ext_unificado,
            dispositivo=dispositivo,
            ip=ip,
        )
    logger.info(
        "Guía %s: Proceso unificado Administrativo terminado por %s (%s). Tipo=%s",
        guia_id, user.get("usuario"), user.get("rol"), tipo_t,
    )
    return True, (
        "Proceso Administrativo terminado correctamente. Guía enviada a CEDIS para su control."
    ), {
        "tipo_transportador": tipo_t,
        "transportador_asignado_id": transportador_asignado_id,
        "externo_con_firma": ext_con_firma,
        "redirect": "/tablero",
    }


def proceso_unificado_cedis(
    guia_id: int,
    user: dict,
    datos: Dict[str, Any],
    dispositivo: str = "web",
    ip: str = "-",
) -> Tuple[bool, str, Dict[str, Any]]:
    """Proceso ÚNICO CEDIS en 1 click: control + entrega transportador/cliente.

    Reglas SPEC v1.0:
    - Sólo ejecutan CEDIS o ADMIN.
    - ESTADOS permitidos: RECIBIDA_ADMIN (recién llega de Admin) o EN_CEDIS (controlado pero no entregado).
    - Tipos de entrega:
        PROPIO:          2 firmas (cedis_entrega + transportador_recibe) → pasa a EN_RUTA
        EXTERNO + FIRMA ADMIN PREVIA: 1 firma (SOLO cedis_entrega; admin ya recogió firma externo) → EN_RUTA
        EXTERNO SIN FIRMA ADMIN (fallback): 2 firmas (cedis_entrega + externo_recibe en CEDIS) → EN_RUTA
        ENVIO DIRECTO:   2 firmas (cedis_entrega + cliente_recibe en persona en CEDIS) → cierra DIRECTAMENTE ENTREGADA (sin transportador)
    - Siempre redirect /tablero.
    """
    requerir_rol(user, "cedis", "admin")
    datos = datos or {}

    g = obtener_guia(guia_id)
    if not g:
        raise GuiaNoExisteError(f"Guía {guia_id} no existe")

    estado_g = g.get("estado") or ""
    if estado_g not in ("RECIBIDA_ADMIN", "EN_CEDIS"):
        raise EstadoInvalidoError(
            "Proceso CEDIS sólo puede ejecutarse sobre guías en RECIBIDA_ADMIN o EN_CEDIS. "
            f"Estado actual: {estado_g}."
        )

    envio_directo = bool(g.get("envio_directo_cedis"))
    tipo_t = (str(g.get("tipo_transportador") or "")).lower()
    hay_admin_firma_ext = bool(obtener_ultima_firma_transportador_admin(guia_id)) if (
        tipo_t == "externo" and not envio_directo
    ) else False

    def _s(v):
        return "" if v is None else str(v).strip()

    # --- Validación común: siempre requiere FIRMA de QUIEN ENTREGA en CEDIS ---
    firma_cedis = _s(datos.get("firma_cedis_entrega") or "")
    if not (firma_cedis.startswith("data:image/") and "," in firma_cedis and len(firma_cedis) >= 80):
        raise ValidationError("Falta la FIRMA de quién entrega en CEDIS (obligatoria)")

    # --- Datos CONTROL CEDIS (si no envían, usar prellenados) ---
    pre = obtener_prellenado_ventas(guia_id) or {}
    def _num(k, min_=0):
        raw = datos.get(k)
        if raw in (None, "", "0", 0):
            raw = pre.get(k) or 0
        try: return max(min_, int(raw))
        except (TypeError, ValueError): return min_
    ctr = {
        "cajas": _num("cajas"),
        "bolsas": _num("bolsas"),
        "cayvas": _num("cayvas"),
        "sobres": _num("sobres"),
        "otros": _s(datos.get("otros") or pre.get("otros") or ""),
        "totales": _num("totales"),
        "vehiculo_cumple": (_s(datos.get("vehiculo_cumple")) or "si").lower() or "si",
        "obs": _s(datos.get("obs") or ""),
        "scan": _s(datos.get("scan") or ""),
        "cedis_funcionario": _s(datos.get("cedis_funcionario") or ""),
        "cedis_funcionario_practicante": _s(datos.get("cedis_funcionario_practicante") or ""),
        "firma": firma_cedis,   # procesar_evento control_cedis pide firma 'firma' como validación
    }
    if ctr["vehiculo_cumple"] not in ("si", "no"):
        ctr["vehiculo_cumple"] = "si"
    # Garantizar: totales = suma de cajas+bolsas+cayvas+sobres (si totales no fue informado explícitamente)
    suma_bultos = ctr["cajas"] + ctr["bolsas"] + ctr["cayvas"] + ctr["sobres"]
    if not datos.get("totales") and suma_bultos > 0:
        ctr["totales"] = suma_bultos
    for c in ("cajas", "bolsas", "cayvas", "sobres"):
        requerir(str(ctr[c]) if ctr[c] > 0 else "0", c, "Valor bulto requerido")  # 0 es válido; el requerimiento es lógico

    # --- Validación: Funcionario CEDIS que entrega (obligatorio) ---
    if not ctr["cedis_funcionario"]:
        raise ValidationError("Debe seleccionar el funcionario CEDIS que realiza la entrega")
    if ctr["cedis_funcionario"] == "PRACTICANTE_PASANTE" and not ctr["cedis_funcionario_practicante"]:
        raise ValidationError("Debe ingresar el nombre del practicante / pasante")

    # --- Preparación de datos 2da firma según caso ---
    entrega_ok: Dict[str, Any] = {}

    # ============ Caso 1: ENVIO DIRECTO (ventas lo marcó → cliente viene personalmente a CEDIS) ============
    if envio_directo:
        # Entrega FINAL al cliente. Estado después: ENTREGADA directo
        nombre_recibe = (
            _s(datos.get("recibe") or "") or
            _s(pre.get("cliente_recibe_nombre") or "")
        ).strip()
        if not nombre_recibe:
            raise ValidationError("Ingrese el NOMBRE COMPLETO de quién recibe en CEDIS (envío directo)")
        firma_cliente = _s(datos.get("firma_recibe") or "")
        if not (firma_cliente.startswith("data:image/") and "," in firma_cliente and len(firma_cliente) >= 80):
            raise ValidationError(
                "Falta la FIRMA DEL CLIENTE que recoge en CEDIS (obligatoria para envío directo; "
                "la guía se cerrará ENTREGADA inmediatamente)."
            )
        # --- Validación: Funcionario CEDIS que entrega (obligatorio también en envío directo) ---
        if not ctr["cedis_funcionario"]:
            raise ValidationError("Debe seleccionar el funcionario CEDIS que realiza la entrega")
        if ctr["cedis_funcionario"] == "PRACTICANTE_PASANTE" and not ctr["cedis_funcionario_practicante"]:
            raise ValidationError("Debe ingresar el nombre del practicante / pasante")
        entrega_ok = {
            "tipo": "ENTREGA_CLIENTE_DIRECTA_CEDIS",
            "evento": "entrega_cliente",
            "recibe": longitud_maxima(nombre_recibe, "recibe", 120),
            "firma": firma_cliente,
            "obs": longitud_maxima(_s(datos.get("obs_entrega") or ""), "obs", 1000),
            "foto": _s(datos.get("foto") or ""),
        }
        # Requerir firma o foto (igual que entrega_cliente en validar_datos_evento):
        ok_firma_cli = isinstance(entrega_ok["firma"], str) and entrega_ok["firma"].startswith("data:image")
        ok_foto_cli = isinstance(entrega_ok["foto"], str) and entrega_ok["foto"].startswith("data:image")
        if not ok_firma_cli and not ok_foto_cli:
            raise ValidationError("Envío directo requiere firma del cliente o foto para cerrar ENTREGADA")

    # ============ Caso 2: FLUJO NORMAL (no es directo) → entrega a transportador → EN_RUTA ============
    else:
        if not tipo_t:
            raise ValidationError(
                "Error: Administrativo aún no ha asignado tipo de transportador (propio/externo). "
                "No se puede procesar en CEDIS."
            )
        # --- Pre-llenar datos SOLO LECTURA transportador (informativos, no se editan aquí) ---
        from guias_coodescor.services.guias_service import obtener_usuario_transportador_por_id as _outi
        transp_nombre = _s(pre.get("transportador_nombre") or "")
        transp_cc = _s(pre.get("transportador_cc") or "")
        transp_tel = _s(pre.get("transportador_tel") or "")
        transp_veh = _s(pre.get("transportador_vehiculo") or "")
        transp_pla = _s(pre.get("transportador_placa") or "")
        transp_fle = _s(pre.get("transportador_flete") or "")
        if tipo_t == "propio":
            tid = g.get("transportador_asignado_id") or 0
            try:
                tid_int = int(tid) or 0
            except (TypeError, ValueError):
                tid_int = 0
            if tid_int > 0:
                _tu = _outi(tid_int)
                if _tu:
                    transp_nombre = transp_nombre or _s(_tu.get("nombre") or "")
                    transp_cc = transp_cc or _s(_tu.get("documento") or "")
                    transp_tel = transp_tel or _s(_tu.get("telefono") or "")
        # --- Firma del recibe (transportador propio/externo fallback) ---
        requiere_segunda_firma = not (tipo_t == "externo" and hay_admin_firma_ext)
        firma_recibe = _s(datos.get("firma_recibe") or "")
        if requiere_segunda_firma:
            # Solicitar NOMBRE que recibe (transportador)
            nombre_recibe_transp = (
                _s(datos.get("transportador_recibe_nombre") or "") or transp_nombre
            ).strip()
            if not nombre_recibe_transp:
                raise ValidationError("Ingrese el nombre del transportador que recibe en CEDIS")
            if not (firma_recibe.startswith("data:image/") and "," in firma_recibe and len(firma_recibe) >= 80):
                if tipo_t == "propio":
                    raise ValidationError("Falta la FIRMA del transportador PROPIO que recibe en CEDIS")
                else:
                    raise ValidationError(
                        "Falta la FIRMA del transportador EXTERNO que recibe en CEDIS "
                        "(no hay firma previa de Administrativo; fallback: debe firmar aquí)."
                    )
            entrega_ok["firma"] = firma_recibe
            transp_nombre = nombre_recibe_transp
        entrega_ok.update({
            "tipo": "ENTREGA_TRANSPORTADOR_CEDIS",
            "evento": "entrega_transporte",
            "nombre": longitud_maxima(transp_nombre, "nombre", 120) or "Transportador",
            "cc": longitud_maxima(transp_cc, "cc", 50),
            "tel": longitud_maxima(transp_tel, "tel", 50),
            "vehiculo": longitud_maxima(transp_veh, "vehiculo", 80),
            "placa": longitud_maxima(transp_pla, "placa", 20),
            "flete": longitud_maxima(transp_fle, "flete", 40),
            "transportador_tipo": tipo_t,
            "hay_admin_firma_externa_prev": hay_admin_firma_ext,
            "requirio_segunda_firma": requiere_segunda_firma,
        })

    # ============ TRANSACCIÓN 1 CLICK ============
    # PASO 1: control_cedis (si estado es EN_CEDIS no se vuelve a ejecutar evento control_cedis.
    #         Solo lo ejecutamos si estado == RECIBIDA_ADMIN)
    ya_tiene_control = False
    from guias_coodescor.services.eventos_service import listar_eventos as _lev_pu
    eventos_previos = _lev_pu(guia_id)
    ya_tiene_control = any(e.get("tipo") == "control_cedis" for e in eventos_previos)
    if not ya_tiene_control:
        procesar_evento(
            guia_id=guia_id,
            tipo_evento="control_cedis",
            user=user,
            datos=ctr,
            dispositivo=dispositivo,
            ip=ip,
        )
    else:
        logger.info(
            "Guía %s: salta control_cedis (ya tiene evento previo de control) en proceso unificado CEDIS", guia_id
        )

    # PASO 2: entrega (entrega_transporte → EN_RUTA, o entrega_cliente → ENTREGADA)
    evento_final = entrega_ok.get("evento")
    if evento_final == "entrega_cliente":
        datos_entrega = {
            "recibe": entrega_ok["recibe"],
            "firma": entrega_ok["firma"],
            "obs": entrega_ok.get("obs") or "",
        }
        if entrega_ok.get("foto"):
            datos_entrega["foto"] = entrega_ok["foto"]
        procesar_evento(guia_id, "entrega_cliente", user, datos_entrega, dispositivo, ip)
        mensaje = (
            "✅ Entrega DIRECTA en CEDIS completada. "
            "Guía marcada como ENTREGADA (cliente confirmó recepción con firma)."
        )
        result_info = {"modo": "entrega_directa_cliente_cedis", "estado": "ENTREGADA"}
    else:
        datos_entrega = {
            "nombre": entrega_ok["nombre"],
            "cc": entrega_ok["cc"],
            "tel": entrega_ok["tel"],
            "vehiculo": entrega_ok["vehiculo"],
            "placa": entrega_ok["placa"],
            "flete": entrega_ok["flete"],
            "firma": entrega_ok.get("firma") or "",
        }
        # Si NO requirió segunda firma (externo + admin ya recogió firma): guardamos la firma CEDIS
        # como evidencia de entrega para auditoría.
        if not datos_entrega["firma"]:
            datos_entrega["firma"] = firma_cedis
            datos_entrega["obs"] = (
                "Entrega EXTERNO con firma previa de Administrativo: "
                "firmó CEDIS como constancia de entrega real."
            )
        procesar_evento(guia_id, "entrega_transporte", user, datos_entrega, dispositivo, ip)
        # -----------------------------------------------------------------------------
        # FIX BUG: Generar TOKEN entrega PÚBLICO AUTOMÁTICAMENTE justo al pasar a EN_RUTA
        # (spec T5 Link activación EN_RUTA = link público /firma/<TOKEN> nace exactamente aquí).
        # No regenerar si ya existía (soporte manual). 1 token único UNIQUE por guía_id.
        # -----------------------------------------------------------------------------
        token_generado: str | None = None
        try:
            from guias_coodescor.services.tokens_service import generar_token_entrega as _gte_loc
            token_generado = _gte_loc(guia_id=guia_id, user=user, regenerar_si_existe=False)
        except Exception as _e:
            logger.warning(
                "Guía %s: no pudo generarse token entrega automático (CEDIS EN_RUTA). "
                "No bloquea el flujo — token aún se puede generar manualmente desde API. Error: %s",
                guia_id, str(_e),
            )
        mensaje = (
            "✅ Proceso CEDIS terminado. Control + Entrega a transportador guardados. "
            "Guía en EN_RUTA (lista para entrega al cliente)."
        )
        result_info = {
            "modo": "entrega_transportador_" + tipo_t,
            "estado": "EN_RUTA",
            "hay_admin_firma_externa_prev": hay_admin_firma_ext,
            "transportador_tipo": tipo_t,
        }
        if token_generado:
            result_info["token"] = token_generado
            result_info["link_publico_entrega"] = f"/firma/{token_generado}"

    logger.info(
        "Guía %s: Proceso unificado CEDIS terminado por %s (%s). Resultado=%s",
        guia_id, user.get("usuario"), user.get("rol"), str(result_info),
    )
    result_info["redirect"] = "/tablero"
    return True, mensaje, result_info


def validar_datos_evento(
    tipo_evento: str,
    datos: Dict[str, Any],
    prellenado: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Valida los datos obligatorios para cada evento.
    Si 'prellenado' viene desde la creación de ventas, completa campos vacíos
    para que CEDIS no tenga que digitar lo que ya está registrado.
    """
    datos = dict(datos or {})
    prellenado = prellenado or {}
    user = user or {}

    def _text(campo, maxlen=200):
        val = datos.get(campo) or ""
        if not isinstance(val, str) or not val.strip():
            val = prellenado.get(campo) or ""
        return longitud_maxima(str(val).strip(), campo, maxlen)

    def _s(v):
        return "" if v is None else str(v).strip()

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
        # --- UNIFICACIÓN lectura firma obligatoria (backward compat 2 nombres):
        #   * "firma"               = nombre oficial del validador (clave genérica)
        #   * "firma_transportador" = legacy/nuevo canvas (HTML data-name en todos los
        #     formularios externo/propio en vista Administrativo y CEDIS)
        #   * adicional por tipo_evento:
        #       - recepcion_admin : "firma_recibido" | "firma_admin" (bug #1 fix)
        #       - entrega_transporte : "firma_cedis_entrega" | "firma_cedis" | "firma_transportador"
        #       - control_cedis     : "firma_cedis_control" | "firma_cedis"
        candidatos_firma = [
            _s(datos.get("firma") or ""),
            _s(datos.get("firma_transportador") or ""),
        ]
        if tipo_evento == "recepcion_admin":
            candidatos_firma += [
                _s(datos.get("firma_recibido") or ""),
                _s(datos.get("firma_admin") or ""),
            ]
        if tipo_evento == "entrega_transporte":
            candidatos_firma += [
                _s(datos.get("firma_cedis_entrega") or ""),
                _s(datos.get("firma_cedis") or ""),
                _s(datos.get("firma_transportador_entrega") or ""),
            ]
        if tipo_evento == "control_cedis":
            candidatos_firma += [
                _s(datos.get("firma_cedis_control") or ""),
                _s(datos.get("firma_cedis") or ""),
            ]
        firma_encontrada = ""
        for fc in candidatos_firma:
            if isinstance(fc, str) and fc.startswith("data:image") and "," in fc and len(fc) >= 80:
                firma_encontrada = fc
                break
        if not firma_encontrada:
            # Mensaje AMIGABLE según tipo evento + nombre campo esperado
            if tipo_evento == "recepcion_admin":
                msg = "Falta la FIRMA DE RECEPCIÓN ADMINISTRATIVA. Dibuja la firma en el primer canvas (arriba)."
            elif tipo_evento == "control_cedis":
                msg = "Falta la FIRMA DE QUIEN HACE EL CONTROL EN CEDIS (canvas Control CEDIS)."
            elif tipo_evento == "entrega_transporte":
                msg = (
                    "Falta firma OBLIGATORIA del transportador (externo) que recibe en CEDIS o "
                    "Administrativo. Dibuja la firma en el canvas correspondiente."
                )
            else:
                msg = "Falta la firma requerida"
            raise ValidationError(msg, "firma")
        # Guardar DOBLE clave para no romper vistas ni consultas que lean cualquiera:
        datos["firma"] = firma_encontrada
        # Conservar el nombre canvas original (si venía) para auditoría:
        if tipo_evento == "entrega_transporte":
            if "firma_transportador" not in datos:
                datos["firma_transportador"] = firma_encontrada
        if tipo_evento == "recepcion_admin":
            if "firma_recibido" not in datos:
                datos["firma_recibido"] = firma_encontrada

    if tipo_evento == "entrega_cliente":
        rol_user = (user or {}).get("rol") or ""
        # SPEC T4: Transportador propio exige DOBLE FIRMA (transportador entrega + cliente recibe)
        if rol_user == "transportador":
            firma_t = datos.get("firma_transportador_entrega") or ""
            if not (isinstance(firma_t, str) and firma_t.startswith("data:image") and len(firma_t) >= 80):
                raise ValidationError(
                    "Falta firma OBLIGATORIA del transportador que entrega la mercancía",
                    "firma_transportador_entrega",
                )
        # Firma cliente o foto: obligatorio 1 de los 2 (todos los roles)
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
        for c in ("cajas", "bolsas", "cayvas", "sobres"):
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
        # TOTAL = suma automática (ignora input usuario para evitar inconsistencia)
        datos["totales"] = int(datos["cajas"]) + int(datos["bolsas"]) + int(datos["cayvas"]) + int(datos["sobres"])
        logger.debug(
            "control_cedis recalcula totales=%d (cajas=%d bolsas=%d cavas=%d sobres=%d)",
            datos["totales"], datos["cajas"], datos["bolsas"], datos["cayvas"], datos["sobres"],
        )
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
    datos_ok = validar_datos_evento(tipo_evento, datos, prellenado=pre, user=user)
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
        "envio_directo_cedis": _bool_flag(datos_nuevos.get("envio_directo_cedis", actual.get("envio_directo_cedis"))),
    }
    # TOTAL se calcula automáticamente (ignora lo que envíe el cliente)
    dn["totales"] = int(dn["cajas"]) + int(dn["bolsas"]) + int(dn["cayvas"]) + int(dn["sobres"])
    logger.debug(
        "editar_guia recalcula totales=%d (cajas=%d bolsas=%d cavas=%d sobres=%d)",
        dn["totales"], dn["cajas"], dn["bolsas"], dn["cayvas"], dn["sobres"],
    )
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


# =================================================================================
# Nuevas funciones: asignar transportador propio/externo y cerrar entrega por TOKEN
# =================================================================================

def asignar_tipo_transportador(
    guia_id: int,
    user: Dict[str, Any],
    tipo: str,
    transportador_asignado_id: Optional[int] = None,
) -> None:
    """SÓLO Administrativo/Admin define tipo transportador para la guía.

    - tipo = 'propio': se guarda transportador_asignado_id (id de usuario rol=transportador)
    - tipo = 'externo': transportador_asignado_id puede ser NULL (se rellenan en entrega_transporte)
    - tipo = None / '' : desasigna
    Permisos: lo pueden hacer 'administrativo', 'admin'. (CEDIS NUNCA)
    """
    from guias_coodescor.config import PERMISO_ASIGNAR_TIPO_TRANSPORTADOR
    roles_lista = sorted(list(PERMISO_ASIGNAR_TIPO_TRANSPORTADOR))
    requerir_rol(user, *roles_lista)
    g = obtener_guia(guia_id)
    if not g:
        raise GuiaNoExisteError(f"Guía {guia_id} no existe")
    tipo_norm = None
    if isinstance(tipo, str):
        t = tipo.strip().lower()
        if t in ("propio", "externo"):
            tipo_norm = t
    if tipo_norm == "propio":
        if not isinstance(transportador_asignado_id, int) or transportador_asignado_id <= 0:
            raise ValidationError("Para transportador PROPIO debe seleccionar un usuario de la lista")
        with db_connection() as conn:
            row = conn.execute(
                "SELECT id, rol, activo FROM usuarios WHERE id = ?",
                (transportador_asignado_id,),
            ).fetchone()
            if not row:
                raise ValidationError("El usuario transportador seleccionado no existe")
            if str(row["rol"]) != "transportador" or int(row["activo"]) != 1:
                raise ValidationError("El usuario seleccionado no es un transportador activo")
    with db_connection(commit=True) as conn:
        conn.execute(
            "UPDATE guias SET tipo_transportador = ?, transportador_asignado_id = ? WHERE id = ?",
            (tipo_norm, transportador_asignado_id if tipo_norm == "propio" else None, guia_id),
        )
    logger.info(
        "Guía %s: tipo_transportador=%s asignado=%s por usuario %s (rol=%s)",
        guia_id, tipo_norm, transportador_asignado_id, user.get("usuario"), user.get("rol"),
    )


def obtener_usuario_transportador_por_id(uid: Optional[int]) -> Optional[Dict[str, Any]]:
    if not uid:
        return None
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id, usuario, nombre, rol, activo FROM usuarios WHERE id = ? AND rol = 'transportador' AND activo = 1",
            (int(uid),),
        ).fetchone()
        return dict(row) if row else None


def cerrar_entrega_por_token_publico(
    token_info: Dict[str, Any],
    datos: Dict[str, Any],
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> int:
    """Cierra la guía vía link público. El cliente NO tiene usuario del sistema.

    - Valida que el token no haya sido usado aún, no esté expirado.
    - Valida los datos del form (firma/foto, nombre recibe) reutilizando validar_datos_evento
      para entrega_cliente (evitamos duplicar lógica).
    - Usuario "virtual": rol=publico (agregado a PERMISO_ADICIONAL_ROL['entrega_cliente']).
    - Marca token como usado (auditoría).
    - Devuelve evento_id de entrega_cliente.
    """
    from guias_coodescor.services.tokens_service import marcar_usado, token_fue_usado

    if token_fue_usado(token_info):
        raise ValidationError("Este link de confirmación ya fue usado. Contacte con Ventas si necesita ayuda.")
    guia_id = int(token_info["guia_id"])
    guia = obtener_guia(guia_id)
    if not guia:
        raise ValidationError("Guía asociada al link no fue encontrada")
    if guia.get("estado") == "ENTREGADA":
        # Ya fue entregada: marcar token usado (idempotencia) y devolver 0 (sin nuevo evento)
        marcar_usado(token_info, ip, ua)
        return 0
    # Usuario virtual público (sin login)
    public_user: Dict[str, Any] = {
        "id": None,
        "usuario": "publico_link_firma",
        "nombre": "Cliente (vía link público)",
        "rol": "publico",
    }
    # Reutilizar toda la lógica de validación de entrega_cliente (firma O foto, recibe, etc.)
    pre = obtener_prellenado_ventas(guia_id)
    datos_ok = validar_datos_evento("entrega_cliente", dict(datos or {}), prellenado=pre)
    # Ejecutar transición: ENTREGA_CLIENTE
    evento_id = procesar_evento(
        guia_id=guia_id,
        tipo_evento="entrega_cliente",
        user=public_user,
        datos=datos_ok,
        dispositivo=f"token_id={token_info['id']}",
        ip=ip,
    )
    # Auditoría: marcar token usado
    marcar_usado(token_info, ip, ua)
    logger.info(
        "Guía %s: ENTREGADA cerrada por token público %s (evento=%s). IP=%s",
        guia_id, token_info.get("token")[:10] + "...", evento_id, ip,
    )
    return evento_id


def registrar_transportador_externo(
    guia_id: int,
    user: dict,
    datos: Dict[str, Any],
    dispositivo: str = "web",
    ip: str = "-",
) -> tuple[bool, str, dict]:
    """Administrativo/Admin registra los DATOS del transportador EXTERNO (y opcionalmente su FIRMA)
    PERO NO EJECUTA EL EVENTO entrega_transporte (NO cambia el estado de la guía).

    Objetivo: que los datos queden disponibles para CEDIS cuando realice la entrega real al transportador,
    siguiendo el flujo correcto:
        VENTAS (CREADA) → ADMIN (RECIBIDA_ADMIN + REGISTRA transportador externo SIN cambiar estado)
                         → CEDIS (control_cedis → EN_CEDIS + entrega_transporte → EN_RUTA)
                         → CLIENTE (ENTREGADA)

    Se guarda en 2 eventos `edicion_guia`:
      1) Uno con los campos del transportador (nombre, cc, tel, vehiculo, placa, flete).
         Automáticamente actualiza el evento CREACIÓN para que obtener_prellenado_ventas() lo vea.
      2) Otro con la FIRMA del transportador (si la hay) como dato JSON auditoría adicional.

    Permisos: admin, administrativo. (CEDIS NUNCA)
    """
    from guias_coodescor.config import PERMISO_REGISTRAR_TRANSPORTADOR_EXTERNO
    roles_lista = sorted(list(PERMISO_REGISTRAR_TRANSPORTADOR_EXTERNO))
    requerir_rol(user, *roles_lista)
    if not isinstance(guia_id, int) or guia_id <= 0:
        raise GuiaError(f"Id guía inválido: {guia_id!r}")
    datos = datos or {}

    def _s(v):
        return "" if v is None else str(v).strip()

    def _l(v, k, n):
        return longitud_maxima(_s(v), k, n)

    # -- Paso 1: edicion_guia con campos del transportador para actualizar prellenado CREACION --
    datos_actualizacion = {
        "transportador_nombre":    _l(datos.get("transportador_nombre"), "transportador_nombre", 120),
        "transportador_cc":        _l(datos.get("transportador_cc"),     "transportador_cc",     50),
        "transportador_tel":       _l(datos.get("transportador_tel"),    "transportador_tel",    50),
        "transportador_vehiculo":  _l(datos.get("transportador_vehiculo"),"transportador_vehiculo",80),
        "transportador_placa":     _l(datos.get("transportador_placa"),  "transportador_placa",  20),
        "transportador_flete":     _l(datos.get("transportador_flete"),  "transportador_flete",  40),
    }
    if datos.get("cliente_recibe_nombre"):
        datos_actualizacion["cliente_recibe_nombre"] = _l(
            datos.get("cliente_recibe_nombre"), "cliente_recibe_nombre", 120,
        )

    procesar_evento(
        guia_id=guia_id,
        tipo_evento="edicion_guia",
        user=user,
        datos=datos_actualizacion,
        dispositivo=dispositivo,
        ip=ip,
    )

    # -- Paso 2: guardar la FIRMA del transportador (si viene) como edicion_guia auditoría extra --
    firma_data_url = _s(datos.get("firma_transportador") or "")
    if firma_data_url and not (
        firma_data_url.startswith("data:image/") and "," in firma_data_url and
        len(firma_data_url) >= 80
    ):
        firma_data_url = ""
    if firma_data_url:
        datos_firma = {
            "motivo": "Registro firma de transportador EXTERNO en bodega (Administrativo/Cedis)",
            "transportador_firma_admin": firma_data_url,
        }
        procesar_evento(
            guia_id=guia_id,
            tipo_evento="edicion_guia",
            user=user,
            datos=datos_firma,
            dispositivo=dispositivo,
            ip=ip,
        )

    logger.info(
        "Guía %s: transportador EXTERNO registrado por %s (usuario %s). "
        "Nombre=%s CC=%s. ConFirma=%s",
        guia_id, user.get("rol"), user.get("usuario"),
        datos_actualizacion["transportador_nombre"] or "-",
        datos_actualizacion["transportador_cc"] or "-",
        bool(firma_data_url),
    )
    return (
        True,
        f"Datos transportador externo guardados correctamente. Quedarán disponibles para CEDIS al entregar.",
        {"actualizado": datos_actualizacion, "con_firma": bool(firma_data_url)},
    )


def obtener_ultima_firma_transportador_admin(guia_id: int) -> Optional[str]:
    """Devuelve la última firma del transportador capturada por Administrativo/Cedis
    (evento edicion_guia con llave transportador_firma_admin).
    CEDIS usa esto para mostrar preview de la firma capturada en Bodega/Administrativa."""
    from guias_coodescor.services.eventos_service import listar_eventos as _le
    evs = sorted(
        [e for e in _le(guia_id) if e.get("tipo") == "edicion_guia"],
        key=lambda e: e.get("creado_en") or "",
    )
    for ev in reversed(evs):
        d = ev.get("datos") or {}
        f = (d or {}).get("transportador_firma_admin") or ""
        if isinstance(f, str) and f.startswith("data:image/") and "," in f and len(f) >= 80:
            return f
    return None

