#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vistas HTML de autenticación (login) y tablero principal (dashboard).
"""
from guias_coodescor.config import ESTADOS
from guias_coodescor.services.guias_service import (
    buscar_guias,
    contar_por_estado,
    listar_guias_por_estado,
)
from guias_coodescor.services.tokens_service import (
    listar_pendientes_confirmacion_link,
)
from guias_coodescor.web.views.base import (
    card_accion,
    escape,
    lista_guias,
    page,
    wrapper_acordeon,
)


def vista_login(ip: str = "", ua: str = "") -> str:
    from guias_coodescor.services.captcha_service import generar_captcha
    _d, svg, token = generar_captcha(ip=ip, ua=ua)
    return page("Ingreso", f"""
    <div class="loginbox"><h1>📦 Guías Coodescor</h1>
    <p class="sub">Acta de entrega de transporte de mercancías · sistema local</p>
    <form data-api="/api/login" data-redirect="/tablero" id="form-login">
      <label>Usuario<input name="usuario" autocomplete="username" required autofocus></label>
      <label>Contraseña<input name="clave" type="password" autocomplete="current-password" required></label>
      <div class="captcha-wrapper" aria-label="Verificación CAPTCHA humana">
        <div class="captcha-head" style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px">
          <label for="captcha-input" style="font-weight:600;font-size:13px;margin:0">
            🔐 Código CAPTCHA
            <span style="display:block;font-weight:400;font-size:12px;color:var(--texto-secundario)">
              ¿Cuál es el código mostrado en la imagen?
            </span>
          </label>
          <button type="button" class="btn-refresh-captcha" id="btn-refresh-captcha"
            title="Generar nuevo código CAPTCHA" aria-label="Recargar código CAPTCHA">
            🔄 Nuevo
          </button>
        </div>
        <div class="captcha-svg-wrap" id="captcha-svg-wrap" style="border-radius:10px;overflow:hidden;margin-bottom:8px">
          {svg}
        </div>
        <label class="sr-only" for="captcha-input">Código CAPTCHA de 6 caracteres</label>
        <input id="captcha-input" type="text" name="captcha_respuesta"
          placeholder="6 caracteres · ej: A3F7K9"
          aria-label="Ingresa el código CAPTCHA de 6 caracteres mostrado en la imagen"
          autocomplete="off" spellcheck="false" required
          inputmode="text" maxlength="8" style="letter-spacing:2px;text-transform:uppercase;font-family:Consolas,ui-monospace,monospace">
        <input type="hidden" name="captcha_token" id="captcha-token" value="{escape(token)}">
      </div>
      <button class="btn primario">Ingresar</button>
    </form>
    <p class="demo">
      Usuarios iniciales:
      <code>admin/admin123</code> ·
      <code>administrativo/adminbod123</code> ·
      <code>ventas/ventas123</code> ·
      <code>ventas2-5/ventas123</code> ·
      <code>cedis/cedis123</code> ·
      <code>cedis2/cedis123</code> ·
      <code>transportador-3/transpor123</code><br>
      CAMBIE LAS CLAVES POR DEFECTO desde el panel Admin.
    </p></div>""")


def vista_tablero(user: dict) -> str:
    rol = user.get("rol", "")
    bloques = []

    # ==============================================================
    # T5 BADGE 🔔 + SECCIÓN ⚠️: Pendientes de confirmación cliente
    #   Roles que ven esta sección: VENTAS, ADMINISTRATIVO, ADMIN
    # ==============================================================
    pendientes_conf_link = []
    cont_badge_pend = 0
    bloque_pend_conf_link_html = ""
    if rol in ("ventas", "administrativo", "admin"):
        pendientes_conf_link = listar_pendientes_confirmacion_link(limite=50)
        cont_badge_pend = len(pendientes_conf_link)
        if cont_badge_pend > 0:
            filas_items = []
            for p in pendientes_conf_link:
                guia_link = f"/guia/{int(p['guia_id'])}"
                emitido_por = (
                    p.get("creado_por_nombre") or p.get("creado_por_usuario") or "-"
                )
                emitido_rol = p.get("creado_rol") or "-"
                creado_en = p.get("creado_en") or "-"
                expira = p.get("expira") or "-"
                consecutivo = escape(str(p.get("consecutivo") or "-"))
                cliente = escape(str(p.get("cliente") or "-"))
                filas_items.append(f"""
                <a href="{guia_link}" class="pend-row" style="display:block;padding:10px 12px;margin:4px 0;border-radius:8px;border:1px solid #fde68a;background:#fffbeb;text-decoration:none;color:#111">
                  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
                    <div style="font-weight:600">📄 Guía N° {consecutivo} · <span style="color:#0f172a">{cliente}</span></div>
                    <span class="chip" style="background:#fbbf24;color:#78350f">⏳ PENDIENTE</span>
                  </div>
                  <div style="font-size:0.9em;color:#475569;margin-top:4px">
                    • Emitido por: <b>{escape(str(emitido_por))}</b> (rol: <b>{escape(str(emitido_rol))}</b>) el {escape(str(creado_en))}<br>
                    • Expira: <b>{escape(str(expira))}</b> · <span style="color:#2563eb">Abrir guía para enviar link al cliente →</span>
                  </div>
                </a>""")
            cuerpo_pend = f"""
  <p class="nota" style="margin:0 0 14px">Links de confirmación <b>ya enviados o generados</b> a clientes y que <b>aún no han sido utilizados</b>. Abre cada guía para reenviar el link por WhatsApp o correo.</p>
  {''.join(filas_items)}"""
            bloque_pend_conf_link_html = wrapper_acordeon(
                "⚠️ Pendientes de confirmación cliente",
                cuerpo_pend,
                subtitulo="Links enviados · esperando firma del cliente",
                badge_texto=f"🔔 {cont_badge_pend}",
                badge_tipo="danger" if cont_badge_pend >= 5 else "aviso",
                abierto_por_defecto=(cont_badge_pend > 0),
                icono_texto="!",
                id_acc="acc-pend-conf",
            )
        else:
            cuerpo_ok = """<p class="nota" style="color:#064e3b;margin-bottom:0">¡Excelente! No hay links de confirmación pendientes por parte de los clientes. Todas las guías están al día.</p>"""
            bloque_pend_conf_link_html = wrapper_acordeon(
                "✅ Pendientes confirmación cliente",
                cuerpo_ok,
                badge_texto="🔔 0",
                badge_tipo="ok",
                icono_texto="✓",
                id_acc="acc-pend-conf",
            )

    # ==============================================================
    # ROL VENTAS → 7 SECCIONES (SPEC v1.0 confirmado)
    # ==============================================================
    if rol == "ventas":
        pend_creadas = listar_guias_por_estado("CREADA", 10)
        pend_cedis = listar_guias_por_estado("EN_CEDIS", 10)
        en_ruta = listar_guias_por_estado("EN_RUTA", 10)
        entregadas_ventas = listar_guias_por_estado("ENTREGADA", 10)
        recibida_admin = listar_guias_por_estado("RECIBIDA_ADMIN", 10)
        bloques.append(bloque_pend_conf_link_html)
        bloques.append(wrapper_acordeon(
            "➕ Crear guía nueva",
            card_accion("➕ Crear guía nueva",
                "Registra cliente, dirección, transportador y opción de envío directo.", "/guia/nueva"),
            subtitulo="Formulario de creación de guías logísticas",
            badge_texto="Acción rápida",
            badge_tipo="primary",
            icono_texto="＋",
        ))
        bloques.append(lista_guias(pend_creadas, "🟡 CREADAS · Esperando recepción Administrativo", rol_usuario=rol))
        bloques.append(lista_guias(recibida_admin, "🔵 RECIBIDA_ADMIN · Procesada por Administrativo", rol_usuario=rol))
        bloques.append(lista_guias(pend_cedis, "🟠 EN_CEDIS · Listas para control en CEDIS", rol_usuario=rol))
        bloques.append(lista_guias(en_ruta, "🚚 EN_RUTA · Generar link de confirmación cliente", rol_usuario=rol))
        bloques.append(lista_guias(entregadas_ventas, "✅ ENTREGADAS · Historial reciente", rol_usuario=rol))

    # ==============================================================
    # ROL ADMINISTRATIVO → 8 SECCIONES (SPEC v1.0)
    # ==============================================================
    if rol == "administrativo":
        pend = listar_guias_por_estado("CREADA", 10)
        recib_admin = listar_guias_por_estado("RECIBIDA_ADMIN", 10)
        en_cedis_adm = listar_guias_por_estado("EN_CEDIS", 10)
        en_ruta_adm = listar_guias_por_estado("EN_RUTA", 10)
        entregadas_adm = listar_guias_por_estado("ENTREGADA", 10)
        anuladas_adm = listar_guias_por_estado("ANULADA", 10)
        bloques.append(bloque_pend_conf_link_html)
        bloques.append(lista_guias(pend, "🟡 CREADAS · Recepción y asignación transportador (1 click)", rol_usuario=rol))
        bloques.append(lista_guias(recib_admin, "🔵 RECIBIDA_ADMIN · Asignadas, pendientes CEDIS", rol_usuario=rol))
        bloques.append(lista_guias(en_cedis_adm, "🟠 EN_CEDIS · En bodega CEDIS, pendientes entrega", rol_usuario=rol))
        bloques.append(lista_guias(en_ruta_adm, "🚚 EN_RUTA · Generar/Compartir link confirmación cliente", rol_usuario=rol))
        bloques.append(lista_guias(entregadas_adm, "✅ ENTREGADAS · Historial reciente", rol_usuario=rol))
        bloques.append(lista_guias(anuladas_adm, "❌ ANULADAS · Guías canceladas", rol_usuario=rol))
        bloques.append(wrapper_acordeon(
            "📊 Exportar auditoría CSV",
            (
                '<a class="btn primario" style="width:100%" href="/api/exportar.csv" download>'
                '⬇️ Descargar archivo CSV auditoría (36 columnas · UTF-8)</a>'
                '<p class="nota" style="margin:14px 0 0">Abre el archivo con Excel, LibreOffice o Google Sheets. '
                'Incluye <b>todos los eventos</b> de cada guía con usuario, rol, fecha y firma hash.</p>'
            ),
            subtitulo="Permiso: Administrativo + Admin Sistema",
            badge_texto="CSV · UTF-8",
            badge_tipo="ok",
            icono_texto="↧",
        ))

    # ==============================================================
    # ROL ADMIN SISTEMA → 8 SECCIONES (SPEC v1.0)
    # ==============================================================
    if rol == "admin":
        pend_adm = listar_guias_por_estado("CREADA", 10)
        rec_adm = listar_guias_por_estado("RECIBIDA_ADMIN", 10)
        cedis_adm = listar_guias_por_estado("EN_CEDIS", 10)
        ruta_adm = listar_guias_por_estado("EN_RUTA", 10)
        ent_adm = listar_guias_por_estado("ENTREGADA", 10)
        an_adm = listar_guias_por_estado("ANULADA", 10)
        bloques.append(bloque_pend_conf_link_html)
        bloques.append(wrapper_acordeon(
            "🛡️ Panel administrativo",
            card_accion("🛡️ Panel administrativo",
                "Usuarios, consecutivo, exportar y anular.", "/admin"),
            subtitulo="Gestión global del sistema",
            badge_texto="Super usuario",
            badge_tipo="primary",
            icono_texto="⚙",
        ))
        bloques.append(lista_guias(pend_adm, "🟡 CREADAS · Ventas", rol_usuario=rol))
        bloques.append(lista_guias(rec_adm, "🔵 RECIBIDA_ADMIN · Administrativo", rol_usuario=rol))
        bloques.append(lista_guias(cedis_adm, "🟠 EN_CEDIS · En bodega", rol_usuario=rol))
        bloques.append(lista_guias(ruta_adm, "🚚 EN_RUTA · En reparto", rol_usuario=rol))
        bloques.append(lista_guias(ent_adm, "✅ ENTREGADAS · Completadas", rol_usuario=rol))
        bloques.append(lista_guias(an_adm, "❌ ANULADAS · Canceladas", rol_usuario=rol))

    # ==============================================================
    # ROL CEDIS → 4 SECCIONES FIJAS (SPEC v1.0 VERBATIM)
    # ==============================================================
    if rol == "cedis":
        ctrl = listar_guias_por_estado("RECIBIDA_ADMIN", 10)
        ced  = listar_guias_por_estado("EN_CEDIS", 10)
        ruta = listar_guias_por_estado("EN_RUTA", 10)
        entreg = listar_guias_por_estado("ENTREGADA", 10)
        bloques.append(lista_guias(ctrl, "1️⃣  RECIBIDA_ADMIN · Por controlar (bultos + vehículo)", rol_usuario=rol))
        bloques.append(lista_guias(ced,  "2️⃣  EN_CEDIS · Controladas, por entregar al transportador", rol_usuario=rol))
        bloques.append(lista_guias(ruta, "3️⃣  EN_RUTA · Entregadas al transportador", rol_usuario=rol))
        bloques.append(lista_guias(entreg, "4️⃣  ✅ ENTREGADAS · Historial procesadas", rol_usuario=rol))

    # ==============================================================
    # ROL TRANSPORTADOR → Header + 3 SECCIONES (SPEC v1.0)
    #   NOTA: Transportador NO TIENE permiso IMPRIMIR (PERMISO_IMPRIMIR_GUIA)
    # ==============================================================
    if rol == "transportador":
        uid = int(user.get("id") or 0)
        mis_en_ruta = buscar_guias(estado="EN_RUTA", transportador_asignado_id=uid, limite=50)
        mis_en_cedis = buscar_guias(estado="EN_CEDIS", transportador_asignado_id=uid, limite=50)
        mis_entregadas = buscar_guias(estado="ENTREGADA", transportador_asignado_id=uid, limite=20)
        header_html = f"""<section class="card" style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8,#0ea5e9);color:#fff;border:none">
          <h3 style="margin-top:0;color:#fff">🚛 Mis entregas · {escape(user.get('nombre') or 'Transportador')}</h3>
          <p style="margin:0;opacity:.95;font-size:14px">Solo aparecen las guías asignadas a tu usuario. Abre cada una EN_RUTA para cerrar la entrega con <b>doble firma (transportador + cliente)</b>.</p>
        </section>"""
        bloques.append(header_html)
        bloques.append(lista_guias(mis_en_ruta, "📦 EN_RUTA · Pendientes por entregar (cerrar con 2 firmas)", rol_usuario=rol))
        bloques.append(lista_guias(mis_en_cedis, "⏳ EN_CEDIS · Próximas a salir de bodega", rol_usuario=rol))
        bloques.append(lista_guias(mis_entregadas, "✅ ENTREGADAS · Historial completadas", rol_usuario=rol))

    # ==============================================================
    # KPIs · con atributo kpi-estado para gradiente superior
    # ==============================================================
    tot = contar_por_estado()
    resumen = "".join(
        f'<div class="kpi" kpi-estado="{escape(r["estado"])}">'
        f'<b>{r["n"]}</b><span>{escape(ESTADOS[r["estado"]][0])}</span></div>'
        for r in tot if r["estado"] in ESTADOS
    )

    # ==============================================================
    # Toolbar buscador + botón Exportar CSV (solo Administrativo + Admin)
    # ==============================================================
    from guias_coodescor.config import PERMISO_EXPORTAR_AUDITORIA
    if rol in PERMISO_EXPORTAR_AUDITORIA:
        toolbar_busc = f"""<div style="display:grid;grid-template-columns:1fr auto;gap:10px;align-items:stretch;margin-bottom:16px">
          <form class="busc" action="/guias" method="get" style="margin:0">
            <input name="q" placeholder="Buscar por consecutivo o cliente…">
            <button class="btn">Buscar</button>
          </form>
          <a class="btn primario" href="/api/exportar.csv" download style="white-space:nowrap">⬇️ Exportar CSV</a>
        </div>"""
    else:
        toolbar_busc = """<form class="busc" action="/guias" method="get">
          <input name="q" placeholder="Buscar por consecutivo o cliente…">
          <button class="btn">Buscar</button></form>"""
    # Título con badge 🔔 si corresponde
    titulo_badge_html = (
        f' <span style="display:inline-block;margin-left:10px;padding:3px 9px;border-radius:999px;'
        f'background:#dc2626;color:#fff;font-size:0.85em;font-weight:700;vertical-align:middle">'
        f'🔔 {cont_badge_pend} pendientes</span>'
        if cont_badge_pend > 0 and rol in ("ventas", "administrativo", "admin")
        else ""
    )
    cuerpo = (
        f"<h2>Hola, {escape(user.get('nombre'))} 👋{titulo_badge_html}</h2>"
        f"<div class='kpis'>{resumen}</div>{toolbar_busc}"
        + "".join(bloques)
    )
    return page("Tablero", cuerpo, user)

