#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vistas HTML: listado de guías, nueva guía, detalle e imprimir.
"""
try:
    import segno
    def _qr_svg(texto):
        return segno.make(texto, error="m").svg_inline(scale=3)
except Exception:
    def _qr_svg(texto):
        return ""

from guias_coodescor.config import ESTADOS, ROL_LABEL, TIPO_TITULO
from guias_coodescor.services.auth_service import obtener_config
from guias_coodescor.services.eventos_service import listar_eventos
from guias_coodescor.services.guias_service import (
    buscar_guias,
    generar_codigo_verificacion,
    obtener_guia,
    obtener_prellenado_ventas,
    obtener_ultima_firma_transportador_admin,
)
from guias_coodescor.services.tokens_service import obtener_info_token_guia, estado_activacion_link
from guias_coodescor.web.views.base import (
    escape,
    estado_chip,
    fila,
    fila_raw,
    img_adj,
    lista_guias,
    page,
    stepper,
)


def _formulario_accion(g: dict, user: dict) -> str:
    rol = user.get("rol", "")
    estado = g.get("estado", "")
    pre = obtener_prellenado_ventas(int(g["id"]))
    gid = int(g["id"])
    from guias_coodescor.services.eventos_service import listar_eventos as _lev_fa
    evs_fa = _lev_fa(gid)
    tiene_transporte = any(e.get("tipo") == "entrega_transporte" for e in evs_fa)
    tiene_entrega_cliente = any(e.get("tipo") == "entrega_cliente" for e in evs_fa)
    tiene_control_local = any(e.get("tipo") == "control_cedis" for e in evs_fa)
    envio_directo_fa = bool(g.get("envio_directo_cedis"))
    tipo_transportador_fa = g.get("tipo_transportador") or ""
    es_propio = tipo_transportador_fa == "propio"
    es_externo = tipo_transportador_fa == "externo"
    transportador_asignado_actual = g.get("transportador_asignado_id") or None

    # ------------------------------------------------------------------
    # ADMINISTRATIVO - PROCESO UNIFICADO (1 click)
    #   Estado CREADA      → formulario completo (todos los campos en 1 solo submit)
    #   Estado >= posterior → banner solo lectura con datos ya procesados
    # ------------------------------------------------------------------
    if rol in ("administrativo", "admin") and not envio_directo_fa:
        # --- Caso 1: guía en CREADA → renderizar formulario UNIFICADO ---
        if estado == "CREADA":
            tipo_actual = tipo_transportador_fa or ""
            checked_prop = tipo_actual == "propio"
            checked_ext  = tipo_actual == "externo"
            checked_none = not tipo_actual
            return f"""<section class="card formbox" id="bloque-admin-unificado"><h3>🛡️ Proceso ÚNICO Administrativo <small>(Recepción + Asignación Transportador · 1 Guardar)</small></h3>
        <p class="nota">Complete <b>TODOS</b> los datos a continuación y presione <b>💾 Guardar</b>.
        El estado pasará a <b>RECIBIDA_ADMIN</b> y la guía se envía automáticamente a <b>CEDIS</b>.</p>
        <form class="form grid" id="form-admin-unificado"
              data-api="/api/guias/{gid}/proceso_administrativo_unificado"
              data-redirect="true"
              data-confirm="¿Guardar el proceso administrativo? · La guía pasará a CEDIS.">
          <div class="subblk info-preview wide">
            <h4>👤 Datos Recepción Administrativa</h4>
            <div class="grid">
              <label class="wide">Recibe (su nombre)<input name="recibe" required value="{escape(user.get('nombre'))}"></label>
            </div>
            <div class="sigbox wide"><span>Firma recepción <b style="color:#dc2626">(OBLIGATORIA)</b>:</span>
              <canvas class="sig" data-name="firma_recibido" width="600" height="180"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar firma</button></div>
          </div>

          <fieldset class="wide">
            <legend>🚛 Tipo de transportador <span style="color:#dc2626">* obligatorio</span></legend>
            <label class="chk"><input type="radio" name="tipo_transportador" value="propio" {"checked" if checked_prop else ""} data-tipo-radio="propio"> 🟢 Transportador PROPIO (operario interno con login)</label>
            <label class="chk"><input type="radio" name="tipo_transportador" value="externo" {"checked" if checked_ext else ""} data-tipo-radio="externo"> 🟡 Transportador EXTERNO (persona externa · datos + firma obligatoria)</label>
          </fieldset>

          <div id="wrap-propios" class="wide" style="display:{'block' if checked_prop else 'none'}">
            <div class="subblk info-preview">
              <h4>🟢 Seleccione transportador propio asignado</h4>
              <label>Seleccione transportador:
                <select name="transportador_asignado_id" id="select-transp-propios-unif" required style="width:100%;margin-top:6px;padding:8px;border-radius:8px;border:1px solid #cbd5e1">
                  <option value="">-- Cargando transportadores... --</option>
                </select>
              </label>
            </div>
          </div>

          <div id="wrap-externo" class="wide" style="display:{'block' if checked_ext else 'none'}">
            <div class="subblk info-preview">
              <h4>🟡 Datos transportador EXTERNO <span style="color:#dc2626">* todos obligatorios</span></h4>
              <div class="grid">
                <label class="wide">Nombre completo<input name="transportador_nombre" required value="{escape(pre.get('transportador_nombre') or '')}" placeholder="Nombre de la persona que transporta"></label>
                <label>CC / Documento<input name="transportador_cc" required value="{escape(pre.get('transportador_cc') or '')}" placeholder="N° identificación"></label>
                <label>Teléfono contacto<input name="transportador_tel" required value="{escape(pre.get('transportador_tel') or '')}" placeholder="300…"></label>
                <label>Vehículo<input name="transportador_vehiculo" value="{escape(pre.get('transportador_vehiculo') or '')}" placeholder="camión / moto…"></label>
                <label>Placa<input name="transportador_placa" value="{escape(pre.get('transportador_placa') or '')}" placeholder="ABC123"></label>
                <label>Valor flete ($)<input name="transportador_flete" value="{escape(pre.get('transportador_flete') or '')}" placeholder="90.000"></label>
              </div>
              <div class="sigbox wide" style="margin-top:10px"><span>Firma DEL TRANSPORTADOR EXTERNO (obligatoria):</span>
                <canvas class="sig" data-name="firma_transportador" width="600" height="220"></canvas>
                <button type="button" class="btn mini" data-limpiar>Limpiar firma</button></div>
            </div>
          </div>

          <button class="btn primario wide" data-confirm="¿Guardar el proceso administrativo? · La guía pasará a CEDIS">
            💾 Guardar proceso Administrativo · Enviar a CEDIS
          </button>
        </form></section>"""

        # --- Caso 2: estado >= RECIBIDA_ADMIN → SOLO LECTURA ---
        if estado in ("RECIBIDA_ADMIN", "EN_CEDIS", "EN_RUTA", "ENTREGADA", "ANULADA"):
            from guias_coodescor.services.eventos_service import listar_eventos as _lev_ro
            evs_ro = _lev_ro(gid)
            adm_ev = next((e for e in evs_ro if e.get("tipo") == "recepcion_admin"), None)
            d_ro = (adm_ev or {}).get("datos", {}) or {}
            nombre_recibe = d_ro.get("recibe") or "-"
            # ---- FIX BUG #5 (doble): ----
            # 1) ANTES leía d_ro.get("firma_archivo"), PERO la firma de recepción
            #    ADMINISTRATIVO NO es un archivo local (/static_file/...); la guardamos
            #    como DATA URL base64 PNG en d_ro["firma"] (y d_ro["firma_recibido"] backup).
            # 2) img_adj(ruta) espera una RUTA LOCAL y hace src="/static_file/{ruta}".
            #    Para DATA URLs necesitamos renderizar <img src="{firma_admin}"> DIRECTAMENTE
            #    sin pasar el prefijo. Por eso creamos función inline:
            def _img_firma(firma_valor: str) -> str:
                if not firma_valor or not isinstance(firma_valor, str):
                    return '<span class="sin">—</span>'
                if firma_valor.startswith("data:image/") and "," in firma_valor:
                    return f'<img class="firma" src="{escape(firma_valor)}" alt="firma" loading="lazy">'
                # Si no empieza por data:image, asumir que es RUTA LOCAL /static_file (archivo)
                return f'<img class="firma" src="/static_file/{escape(firma_valor)}" alt="firma" loading="lazy">'

            # Leer firma recepción ADMIN (prioridad 1: "firma" ; backup "firma_recibido")
            firma_admin = (
                (d_ro.get("firma") if isinstance(d_ro.get("firma"), str) else "")
                or (d_ro.get("firma_recibido") if isinstance(d_ro.get("firma_recibido"), str) else "")
                or (d_ro.get("firma_archivo") if isinstance(d_ro.get("firma_archivo"), str) else "")
                or ""
            )
            from guias_coodescor.services.guias_service import obtener_usuario_transportador_por_id as _outi_ro
            transp_asig = ""
            if transportador_asignado_actual:
                _tu = _outi_ro(int(transportador_asignado_actual))
                if _tu:
                    transp_asig = f"{escape(_tu.get('nombre') or '')} ({escape(_tu.get('usuario') or '')})"
            badge_tipo = ""
            if es_propio:
                badge_tipo = '<span class="chip ok">PROPIO · con usuario</span>'
            elif es_externo:
                badge_tipo = '<span class="chip" style="background:#d97706;color:#fff">EXTERNO · sin usuario</span>'
            info_transp = ""
            if es_propio and transp_asig:
                info_transp = fila("Transportador asignado", transp_asig)
            elif es_externo:
                # FIX BUG #5: obtener_ultima_firma_transportador_admin() lee evento edicion_guia
                # y busca "transportador_firma_admin". ADEMÁS agregamos FALLBACK con
                # pre.get("transportador_firma_admin") (merge de obtener_prellenado_ventas nuevo)
                # ya que ahora el unificado guarda TODO en un evento edicion_guia.
                firma_ext = (
                    (pre.get("transportador_firma_admin") if isinstance(pre.get("transportador_firma_admin"), str) else "")
                    or obtener_ultima_firma_transportador_admin(gid)
                    or ""
                )
                firma_ext_html = ""
                if firma_ext and firma_ext.startswith("data:image/"):
                    firma_ext_html = f'<div class="kv"><span>Firma (capturada por Administrativo)</span><b><img src="{escape(firma_ext)}" class="firma" alt="firma transportador externo"></b></div>'
                info_transp = (
                    fila("Nombre transportador", pre.get("transportador_nombre")) +
                    fila("CC / Documento", pre.get("transportador_cc")) +
                    fila("Teléfono", pre.get("transportador_tel")) +
                    fila("Vehículo", pre.get("transportador_vehiculo")) +
                    fila("Placa", pre.get("transportador_placa")) +
                    fila("Valor flete", pre.get("transportador_flete")) +
                    firma_ext_html
                )
            return f"""<section class="card formbox info"><h3>✅ Proceso Administrativo YA ejecutado {badge_tipo}</h3>
            <div class="subblk info-preview">
              <h4>Registro guardado</h4>
              <div class="grid">
                {fila("Recibe (Administrativo)", nombre_recibe)}
                {fila("Fecha/hora", (adm_ev or {}).get("en", "-"))}
                {info_transp}
              </div>
              <div class="kv"><span>Firma recepción</span><b>{_img_firma(firma_admin)}</b></div>
            </div>
            <p class="nota">Este paso ya se cerró. La guía se encuentra en el siguiente estado del flujo (CEDIS o posterior).</p>
            </section>"""

    # ------------------------------------------------------------------
    # TRANSPORTADOR PROPIO - entrega en terreno a cliente
    # ------------------------------------------------------------------
    if rol == "transportador" and estado == "EN_RUTA" and tiene_transporte and not tiene_entrega_cliente:
        nombre_p = pre.get("cliente_recibe_nombre") or ""
        return f"""<section class="card formbox"><h3>✅ Entrega al cliente · Transportador propio <span class="chip ok">2 firmas obligatorias</span></h3>
        <p class="nota">Usted fue asignado como transportador para esta guía.
        <b>REGLAS:</b> 1️⃣ <b>Primero firme USTED</b> (transportador que entrega), luego solicite a la persona que
        recibe que <b>firme o adjunte foto</b>. Al guardar la guía quedará <b>ENTREGADA</b> y volverá al tablero.</p>
        <div class="subblk info-preview">
          <h4>👤 Datos informados por Ventas · confirmar con quien recibe</h4>
          <div class="grid">
            {fila('Cliente', g.get('cliente'))}
            {fila('Dirección', g.get('direccion'))}
            {fila('Nombre persona que recibe', nombre_p)}
            {fila('Documento / CC', pre.get('transportador_cc'))}
            {fila('Teléfono', pre.get('transportador_tel'))}
          </div></div>
        <form class="form grid" data-api="/api/guias/{gid}/entrega_cliente" data-redirect="true">
          <div class="subblk info-preview wide">
            <h4>1️⃣ Firma del TRANSPORTADOR <small>(USTED · quién entrega la mercancía)</small> <span style="color:#dc2626">*obligatoria</span></h4>
            <div class="sigbox wide"><span>Firma de <b>{escape(user.get('nombre') or user.get('usuario') or 'Transportador')}</b> (transportador entrega):</span>
              <canvas class="sig" data-name="firma_transportador_entrega" width="600" height="200"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar mi firma</button></div>
          </div>
          <div class="subblk info-preview wide">
            <h4>2️⃣ Datos y firma del CLIENTE <small>(quién recibe)</small></h4>
            <label class="wide">Recibe (nombre completo de QUIÉN FIRMA)<input name="recibe" required value="{escape(nombre_p)}" placeholder="Nombre completo de quien recibe en la entrega final"></label>
            <div class="sigbox wide"><span>Firma del cliente <small>(o foto debajo si no puede firmar)</small>:</span>
              <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar firma cliente</button></div>
            <label class="wide">📷 Foto evidencia (opcional si hay firma cliente · obligatorio si NO firma)
              <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
            <label class="wide">Observaciones de la entrega<textarea name="obs" rows="2" placeholder="Ej: Recibe auxiliar de bodega, facturas 20929-20930, todo en orden."></textarea></label>
          </div>
          <button class="btn primario wide" data-confirm="¿Confirmar ENTREGA FINAL al cliente? · La guía quedará ENTREGADA y volverá al Tablero">✅ Confirmar entrega final · Cerrar guía</button></form>
          <p class="nota">Se exige <b>(1) firma transportador OBLIGATORIA + (2) firma cliente O foto</b> para cerrar.</p></section>"""

    # ------------------------------------------------------------------
    # CEDIS - PROCESO ÚNICO UNIFICADO (1 click)
    #   Estados válidos: RECIBIDA_ADMIN (recién llega) o EN_CEDIS (ya controlado, sin entregar aún)
    #   Tipos: ENVIO_DIRECTO / PROPIO / EXTERNO(c/firma admin) / EXTERNO(s/firma admin fallback)
    #   Después de ENTREGADO/A → banner solo lectura
    # ------------------------------------------------------------------
    if rol in ("cedis", "admin") and not tiene_transporte and estado in ("RECIBIDA_ADMIN", "EN_CEDIS"):
        # ========== Caso 1: envio directo (cliente recoge en persona en CEDIS - CIERRE DIRECTO ENTREGADA) ==========
        if envio_directo_fa:
            nombre_p = pre.get("cliente_recibe_nombre") or ""
            doc_p = pre.get("transportador_cc") or ""
            tel_p = pre.get("transportador_tel") or ""
            veh_p = pre.get("transportador_vehiculo") or ""
            placa_p = pre.get("transportador_placa") or ""
            obs_p = pre.get("transportador_nombre") or ""
            info_preview = ""
            if nombre_p or doc_p or tel_p:
                info_preview = f"""<div class="subblk info-preview wide">
                  <h4>👤 Datos informados por Ventas · confirme con la persona que recoge</h4>
                  <div class="grid">
                    {fila('Nombre completo (esperado)', nombre_p)}
                    {fila('Documento / CC', doc_p)}
                    {fila('Teléfono', tel_p)}
                    {fila('Vehículo (si viene)', veh_p)}
                    {fila('Placa (si viene)', placa_p)}
                    {fila('Observación entrega', obs_p)}
                  </div></div>"""
            return f"""<section class="card formbox" id="bloque-cedis-unificado"><h3>📦 Proceso ÚNICO CEDIS · Envío DIRECTO <span class="chip ok">cierre directo ENTREGADA</span></h3>
        <p class="nota"><b>Envío DIRECTO a CEDIS:</b> la mercancía la recoge <b>personalmente el cliente en CEDIS</b>.
        Confirme bultos, solicite <b>firma o foto</b> y cierre la guía. <b>Queda ENTREGADA inmediatamente</b>.</p>
        <form class="form grid" id="form-cedis-unif" data-api="/api/guias/{gid}/proceso_cedis_unificado" data-redirect="true" data-modo="directo">
          <div class="subblk info-preview wide">
            <h4>1️⃣ Control CEDIS · bultos <small>(confirme o corrija)</small></h4>
            <div class="bultos-grid">
              <label>N° cajas<input name="cajas" type="number" min="0" value="{int(pre.get('cajas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° bolsas<input name="bolsas" type="number" min="0" value="{int(pre.get('bolsas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° cavas<input name="cayvas" type="number" min="0" value="{int(pre.get('cayvas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° sobres<input name="sobres" type="number" min="0" value="{int(pre.get('sobres') or 0)}" class="bulto-input" data-bulto></label>
              <label>Otros<input name="otros" placeholder="…" value="{escape(pre.get('otros') or '')}"></label>
              <label class="total-bultos">Total unidades<input name="totales" type="number" min="0" value="{int(pre.get('totales') or 0)}" readonly data-total-unidades></label>
            </div>
            <fieldset><legend>Vehículo de la persona (si viene en carro/moto)</legend>
              <label class="chk"><input type="radio" name="vehiculo_cumple" value="si" checked> Condiciones buenas</label>
              <label class="chk"><input type="radio" name="vehiculo_cumple" value="no"> No cumple</label>
            </fieldset>
            <label class="wide">Observaciones<textarea name="obs" rows="2" placeholder="Ej: 3 cajas + 1 cava, todo en orden"></textarea></label>
            <label class="wide">Funcionario CEDIS que entrega <span style="color:#dc2626">*obligatorio</span>
              <select name="cedis_funcionario" id="select-cedis-funcionario" required>
                <option value="">-- Seleccione funcionario --</option>
                <option value="Aldair Hoyos">Aldair Hoyos</option>
                <option value="Nel Guerra">Nel Guerra</option>
                <option value="Mario Wilchez">Mario Wilchez</option>
                <option value="Danilo Gomez">Danilo Gomez</option>
                <option value="Lida Perez">Lida Perez</option>
                <option value="PRACTICANTE_PASANTE">Practicante / Pasante (escribir nombre)</option>
              </select>
              <input type="text" name="cedis_funcionario_practicante" id="input-cedis-practicante" placeholder="Nombre del practicante / pasante" style="display:none; margin-top:6px;" autocomplete="off">
            </label>
            <div class="sigbox wide"><span>Firma de QUIEN ENTREGA en CEDIS <span style="color:#dc2626">*obligatoria</span>:</span>
              <canvas class="sig" data-name="firma_cedis_entrega" width="600" height="200"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          </div>
          {info_preview}
          <div class="subblk info-preview wide">
            <h4>2️⃣ Entrega a cliente que recoge · Firma cliente <span style="color:#dc2626">*obligatoria o foto</span></h4>
            <label class="wide">Recibe (nombre completo de QUIEN FIRMA)<input name="recibe" required value="{escape(nombre_p)}" placeholder="Nombre completo de la persona que recoge en CEDIS"></label>
            <div class="sigbox wide"><span>Firma del cliente:</span>
              <canvas class="sig" data-name="firma_recibe" width="600" height="220"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar firma</button></div>
            <label class="wide">📷 Foto evidencia (opcional si hay firma · obligatorio si no firma)
              <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
            <label class="wide">Observaciones entrega<textarea name="obs_entrega" rows="2" placeholder="Ej: Recibe auxiliar bodega, facturas FV 20929-20930 entregadas"></textarea></label>
          </div>
          <button class="btn primario wide" data-confirm="¿CONFIRMAR entrega DIRECTA en CEDIS? · La guía QUEDARÁ ENTREGADA y cerrada">✅ Confirmar · cerrar ENTREGADA</button>
        </form></section>"""

        # ========== Caso 2: flujo NORMAL (sin envío directo) → entrega a transportador → EN_RUTA ==========
        # Primero: validar que el administrativo ya haya asignado tipo.
        if not tipo_transportador_fa:
            return f"""<section class="card formbox warning" id="bloque-cedis-unificado"><h3>⚠️ Pendiente: Administrativo aún no asigna tipo transportador</h3>
            <p class="nota"><b>CEDIS NO puede asignar tipo de transportador</b> (solo lo hace Administrativo).
            Antes de procesar esta guía, debe ser procesada por Administrativo (recepción + asignación PROPIO/EXTERNO).
            <br>Una vez listo, actualice la página para ver el formulario unificado de entrega.</p></section>"""
        # Datos transportador SOLO LECTURA (se pueden confirmar visualmente)
        from guias_coodescor.services.guias_service import obtener_usuario_transportador_por_id as _outi_ce
        _nombre_t = pre.get("transportador_nombre") or ""
        _doc_t = pre.get("transportador_cc") or ""
        _tel_t = pre.get("transportador_tel") or ""
        _veh_t = pre.get("transportador_vehiculo") or ""
        _placa_t = pre.get("transportador_placa") or ""
        _fle_t = pre.get("transportador_flete") or ""
        if es_propio and transportador_asignado_actual:
            try:
                _tid = int(transportador_asignado_actual)
                _tu = _outi_ce(_tid) if _tid else None
                if _tu:
                    _nombre_t = _nombre_t or (_tu.get("nombre") or "")
                    _doc_t = _doc_t or (_tu.get("documento") or "")
                    _tel_t = _tel_t or (_tu.get("telefono") or "")
            except (TypeError, ValueError):
                pass
        # Validar: externo ya tiene firma Admin?
        hay_firma_admin_ext = bool(obtener_ultima_firma_transportador_admin(gid)) if es_externo else False
        badge_t = ('<span class="chip ok">PROPIO</span>' if es_propio else
                   '<span class="chip" style="background:#d97706;color:#fff">EXTERNO</span>')
        info_transp_header = ""
        if es_externo and hay_firma_admin_ext:
            info_transp_header = f"""<div class="subblk info-preview wide">
              <h4>ℹ️ Firma del transportador EXTERNO ya capturada por <b>Administrativo</b> ✓</h4>
              <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
                <img src="{escape(obtener_ultima_firma_transportador_admin(gid))}" style="border:1px dashed #aaa;max-width:340px;max-height:140px;background:#fff" alt="firma admin transportador">
                <small class="nota">El transportador ya firmó en Bodega/Administrativa. <b>EN ESTE PASO SOLO FIRMA CEDIS</b> como constancia de entrega real; no se vuelve a pedir firma al transportador.</small>
              </div></div>"""
        requiere_segunda_firma = not (es_externo and hay_firma_admin_ext)
        label_segunda_firma = (
            "Firma del TRANSPORTADOR PROPIO que recibe en CEDIS" if es_propio else
            "Firma del TRANSPORTADOR EXTERNO que recibe en CEDIS (fallback - no hubo firma en Admin)"
        )
        return f"""<section class="card formbox" id="bloque-cedis-unificado"><h3>📦 Proceso ÚNICO CEDIS · Control + Entrega transportador {badge_t}</h3>
        <p class="nota">Complete los datos de control y las firmas correspondientes →
        <b>1 solo click → 1 transacción → EN_RUTA</b>.</p>
        <form class="form grid" id="form-cedis-unif" data-api="/api/guias/{gid}/proceso_cedis_unificado" data-redirect="true" data-modo="transportador">
          <div class="subblk info-preview wide">
            <h4>1️⃣ Control CEDIS · bultos <small>(confirme o corrija desde Ventas)</small></h4>
            <div class="bultos-grid">
              <label>N° cajas<input name="cajas" type="number" min="0" value="{int(pre.get('cajas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° bolsas<input name="bolsas" type="number" min="0" value="{int(pre.get('bolsas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° cavas<input name="cayvas" type="number" min="0" value="{int(pre.get('cayvas') or 0)}" class="bulto-input" data-bulto></label>
              <label>N° sobres<input name="sobres" type="number" min="0" value="{int(pre.get('sobres') or 0)}" class="bulto-input" data-bulto></label>
              <label>Otros<input name="otros" placeholder="…" value="{escape(pre.get('otros') or '')}"></label>
              <label class="total-bultos">Total unidades<input name="totales" type="number" min="0" value="{int(pre.get('totales') or 0)}" readonly data-total-unidades></label>
            </div>
            <label>Código escaneado (lector)<input name="scan" placeholder="opcional · lector USB"></label>
            <fieldset><legend>Condiciones del vehículo de carga</legend>
              <label class="chk"><input type="radio" name="vehiculo_cumple" value="si" checked> Cumple</label>
              <label class="chk"><input type="radio" name="vehiculo_cumple" value="no"> No cumple</label>
            </fieldset>
            <label class="wide">Observaciones<textarea name="obs" rows="2"></textarea></label>
            <label class="wide">Funcionario CEDIS que entrega <span style="color:#dc2626">*obligatorio</span>
              <select name="cedis_funcionario" id="select-cedis-funcionario" required>
                <option value="">-- Seleccione funcionario --</option>
                <option value="Aldair Hoyos">Aldair Hoyos</option>
                <option value="Nel Guerra">Nel Guerra</option>
                <option value="Mario Wilchez">Mario Wilchez</option>
                <option value="Danilo Gomez">Danilo Gomez</option>
                <option value="Lida Perez">Lida Perez</option>
                <option value="PRACTICANTE_PASANTE">Practicante / Pasante (escribir nombre)</option>
              </select>
              <input type="text" name="cedis_funcionario_practicante" id="input-cedis-practicante" placeholder="Nombre del practicante / pasante" style="display:none; margin-top:6px;" autocomplete="off">
            </label>
            <div class="sigbox wide"><span>Firma de QUIEN ENTREGA en CEDIS <span style="color:#dc2626">*obligatoria</span>:</span>
              <canvas class="sig" data-name="firma_cedis_entrega" width="600" height="200"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          </div>
          <div class="subblk info-preview wide">
            <h4>2️⃣ Datos Transportador <small>(informados por Administrativo · solo lectura confirmación)</small></h4>
            <div class="grid">
              {fila('Tipo transportador', 'PROPIO (con login)' if es_propio else 'EXTERNO (sin login)')}
              {fila('Nombre transportador', _nombre_t)}
              {fila('Documento / CC', _doc_t)}
              {fila('Teléfono', _tel_t)}
              {fila('Vehículo', _veh_t)}
              {fila('Placa', _placa_t)}
              {fila('Valor flete ($)', _fle_t)}
            </div>
            <input type="hidden" name="transportador_recibe_nombre" value="{escape(_nombre_t)}">
          </div>
          {info_transp_header}
          <div class="subblk info-preview wide" id="wrap-segunda-firma-cedis" style="display:{'block' if requiere_segunda_firma else 'none'}">
            <h4>3️⃣ Firma del transportador que recibe <span style="color:#dc2626">*obligatoria{' · FALLBACK' if es_externo else ''}</span></h4>
            <div class="sigbox wide"><span>{label_segunda_firma}:</span>
              <canvas class="sig" data-name="firma_recibe" width="600" height="220"></canvas>
              <button type="button" class="btn mini" data-limpiar>Limpiar firma</button></div>
          </div>
          <button class="btn primario wide" data-confirm="¿Confirmar Proceso ÚNICO CEDIS? · Control + Entrega = EN_RUTA">✅ Guardar proceso CEDIS · pasar a EN_RUTA</button>
        </form></section>"""

    # ------------------------------------------------------------------
    # CEDIS: ya fue procesado (tiene entrega_transporte) → banner solo lectura
    # ------------------------------------------------------------------
    if rol == "cedis" and (tiene_transporte or estado in ("EN_RUTA", "ENTREGADA", "ANULADA")):
        cierre_ok = "<span class='chip ok'>✓ Entrega hecha</span>" if tiene_transporte else ""
        # Obtener funcionario CEDIS si existe en el evento control_cedis
        ev_ctrl = ev.get("control_cedis")
        datos_ctrl = (ev_ctrl or {}).get("datos", {}) or {}
        funcionario_cedis = datos_ctrl.get("cedis_funcionario") or ""
        funcionario_practicante = datos_ctrl.get("cedis_funcionario_practicante") or ""
        func_display = funcionario_cedis
        if funcionario_cedis == "PRACTICANTE_PASANTE" and funcionario_practicante:
            func_display = f"{funcionario_cedis} → {funcionario_practicante}"
        elif funcionario_cedis:
            func_display = funcionario_cedis
        else:
            func_display = "— (no registrado)"
        return f"""<section class="card formbox info"><h3>✅ Proceso CEDIS ya ejecutado {cierre_ok}</h3>
        <p class="nota">Esta guía ya fue procesada por CEDIS (control + entrega). Se encuentra en estado <b>{estado}</b>.
        <br>Si requiere modificar algo, contacte al administrador del sistema.</p>
        <div class="subblk info-preview wide">
          <h4>👷 Funcionario CEDIS que realizó la entrega</h4>
          <div class="grid">
            {fila('Funcionario', func_display)}
          </div>
        </div></section>"""

    # Admin - anular
    if rol == "admin" and estado not in ("ENTREGADA", "ANULADA"):
        return f"""<section class="card formbox danger"><h3>⚠️ Anular guía</h3>
        <form class="form" data-api="/api/guias/{gid}/anular" data-redirect="true" data-confirm="¿Anular definitivamente esta guía?">
          <label>Motivo<input name="motivo" required></label>
          <button class="btn peligro">Anular</button></form></section>"""
    return ""


def vista_nueva_guia(user: dict) -> str:
    if user.get("rol") != "ventas":
        return page("Nueva guía", "<p class='sin'>Solo el área de Ventas crea guías.</p>", user)
    from guias_coodescor.database.models import get_config as _gc
    lista_clientes = _gc("lista_clientes_json", "[]") or "[]"
    cuerpo = f"""<h2>Nueva guía <small>bloque VENTAS</small></h2>
    <form class="card form grid" data-api="/api/guias" data-redirect="true" id="form-nueva-guia">
      <label class="ac-nit-wrap" id="wrap-nit">
        NIT <small class="ac-nit-hint">Escribe y selecciona para autocompletar · <kbd>↓</kbd><kbd>↑</kbd> navegar · <kbd>↵</kbd> seleccionar · <kbd>Esc</kbd> cerrar</small>
        <input name="nit" id="input-nit" placeholder="NIT o documento empresa (ej: 900123456-7)" autocomplete="off" aria-autocomplete="list" aria-controls="panel-nit" aria-expanded="false">
        <div class="ac-nit-panel" id="panel-nit" role="listbox"></div>
      </label>
      <datalist id="lista-nits"></datalist>
      <label>Cliente<input name="cliente" id="input-cliente" required placeholder="Aristo Farmacéutica SAS" list="lista-clientes-vta"></label>
      <datalist id="lista-clientes-vta"></datalist>
      <label>Centro de operación
        <select name="centro_operacion" required>
          <option value="-" selected>— (Oficina central)</option>
          <option value="1000">1000</option>
          <option value="1100">1100</option>
          <option value="1200">1200</option>
          <option value="1300">1300</option>
          <option value="1400">1400</option>
          <option value="1500">1500</option>
          <option value="1600">1600</option>
          <option value="1700">1700</option>
          <option value="1800">1800</option>
          <option value="1900">1900</option>
          <option value="2000">2000</option>
          <option value="2100">2100</option>
          <option value="2200">2200</option>
        </select>
      </label>
      <label class="wide">Dirección<input name="direccion" id="input-direccion" placeholder="Cl 27 # 10-23"></label>
      <label>Ciudad<input name="ciudad" required placeholder="Montería" list="lista-ciudades"></label>
      <datalist id="lista-ciudades">
        <option value="Montería"><option value="Cereté"><option value="Sahagún">
        <option value="Lorica"><option value="Planeta Rica"><option value="Montelíbano">
      </datalist>
      <section class="multi-docs wide" id="multi-docs-nueva-guia" data-prefix-options="FV,TB,PD,TR" data-default-prefix="FV">
        <h4 class="doc-tit">📄 Documentos incluidos <span class="badge-mini" id="docs-count-badge">1</span></h4>
        <div class="doc-wrapper" id="docs-wrapper"></div>
        <div class="doc-tools">
          <button type="button" class="btn-agregar-doc" id="btn-agregar-doc">+ Agregar otro documento</button>
          <span class="doc-ayuda">Combina <b>FV + TB + PD + TR</b> en la misma operación. Cada línea = un par (Prefijo · N°). Duplicados se rechazan.</span>
        </div>
        <div class="doc-validaciones" id="docs-validaciones"></div>
      </section>
      <input type="hidden" name="documentos_json" id="documentos_json">
      <input type="hidden" name="prefijo" id="prefijo-hidden-legacy">
      <input type="hidden" name="documentos" id="documentos-hidden-legacy">
      <label class="chk enviodirecto-label">
        <input type="checkbox" name="generar_link_recibido" id="chk-generar-link-recibido" value="1">
        <div class="enviodirecto-content">
          <div class="enviodirecto-title">🔗 Generar link de recibido AHORA (Ventas)</div>
          <div class="enviodirecto-sub">Marca esta casilla para generar el link público de confirmación / firma de entrega inmediatamente al crear la guía.<br>Podrás compartirlo con el cliente por WhatsApp sin esperar el paso CEDIS.</div>
        </div>
      </label>
      <label class="wide">Observaciones ventas
        <small class="ayuda">Separa cada N° de factura, remisión o documento con <b>guion (-)</b> para identificarlos luego (ej: FV 20929 - REM 456 - NOTA 78)</small>
        <textarea name="obs_ventas" rows="3" placeholder="Ej: FV 20929 - REM 456 - NOTA 78 - Urgente entregar a recepción"></textarea>
      </label>

      <fieldset class="wide bultos-ventas"><legend>📦 Bultos informados por Ventas <small>(CEDIS confirmará/editará)</small></legend>
        <div class="bultos-grid">
          <label>N° cajas<input name="cajas" type="number" min="0" value="0" class="bulto-input" data-bulto></label>
          <label>N° bolsas<input name="bolsas" type="number" min="0" value="0" class="bulto-input" data-bulto></label>
          <label>N° cavas<input name="cayvas" type="number" min="0" value="0" class="bulto-input" data-bulto></label>
          <label>N° sobres<input name="sobres" type="number" min="0" value="0" class="bulto-input" data-bulto></label>
          <label>Otros<input name="otros" placeholder="detalle"></label>
          <label class="total-bultos">Total unidades<input name="totales" type="number" min="0" value="0" readonly data-total-unidades title="Calculado automáticamente = cajas + bolsas + cavas + sobres"></label>
        </div>
      </fieldset>

      <fieldset class="wide" id="bloque-cliente-recoge"><legend>🏃 Cliente / Persona que retira o recibe <small>(quien viene por el pedido)</small></legend>
        <p class="nota">Llena estos campos cuando <b>el cliente viene personalmente por su pedido</b>. CEDIS confirmará los datos al entregar. Si hay transportador, CEDIS lo diligencia luego.</p>
        <div class="grid">
          <label class="wide">Nombre completo<input name="cliente_recibe_nombre" id="input-recibe" placeholder="Nombre de la persona que recibe"></label>
          <label>Documento / CC<input name="transportador_cc" placeholder="cédula o documento"></label>
          <label>Teléfono<input name="transportador_tel" placeholder="300…"></label>
          <label>Vehículo (si aplica)<input name="transportador_vehiculo" placeholder="carro / moto / camioneta"></label>
          <label>Placa (si aplica)<input name="transportador_placa" placeholder="ABC123"></label>
          <label>Observación entrega<input name="transportador_nombre" placeholder="Detalles · ej: Retira auxiliar bodega"></label>
        </div>
      </fieldset>

      <hr class="wide">

      <div class="wide enviodirecto-card" id="envio-directo-wrap">
        <label class="chk enviodirecto-label">
          <input type="checkbox" name="envio_directo_cedis" id="chk-envio-directo" value="1">
          <div class="enviodirecto-content">
            <div class="enviodirecto-title">🚀 ENVIAR DIRECTAMENTE A CEDIS</div>
            <div class="enviodirecto-sub">Marca esta casilla para SALTAR el paso de recepción Bodega / Administrativa.
            La guía queda lista para Control CEDIS inmediatamente.</div>
          </div>
        </label>
      </div>

      <label>Entrega (quien despacha)<input name="entrega_nombre" required value="{escape(user.get('nombre'))}"></label>

      <button class="btn primario wide" id="btn-crear-guia">💾 Crear guía</button>
    </form>

    <div id="clientes-data" style="display:none" data-json="{escape(lista_clientes)}"></div>
"""
    return page("Nueva guía", cuerpo, user)


def vista_listado_guias(user: dict, qs: dict) -> str:
    q = (qs.get("q", [""])[0] or "").strip()
    est = (qs.get("estado", [""])[0] or "").strip()
    rows = buscar_guias(q=q, estado=est, limite=200)
    opts = "".join(
        f"<option value='{k}'>{escape(v[0])}</option>"
        for k, v in ESTADOS.items()
    )
    if rows:
        lista_html = lista_guias(rows, "Resultados")
        lista_html = (lista_html
            .replace("</section>", "")
            .replace("<section class='card'>", "")
            .replace("<h3>Resultados</h3>", ""))
    else:
        lista_html = "<p class='sin'>Sin resultados</p>"
    cuerpo = f"""<h2>Guías</h2>
    <form class="busc" method="get" action="/guias">
      <input name="q" value="{escape(q)}" placeholder="Consecutivo o cliente…">
      <select name="estado"><option value="">Todos los estados</option>{opts}</select>
      <button class="btn">Filtrar</button></form>
    <div class="lista">{lista_html}</div>"""
    return page("Guías", cuerpo, user)


def vista_detalle_guia(guia_id: int, user: dict) -> str:
    g = obtener_guia(guia_id)
    if not g:
        return page("Guía", "<p class='sin'>Guía no encontrada.</p>", user)
    evs = listar_eventos(guia_id)
    ev = {x["tipo"]: x for x in evs}
    cre, adm = ev.get("creacion"), ev.get("recepcion_admin")
    ctrl, trn = ev.get("control_cedis"), ev.get("entrega_transporte")
    cli = ev.get("entrega_cliente")
    cod = generar_codigo_verificacion(g)
    qr = _qr_svg(f"GUIA-{g['consecutivo']}-{cod}")
    pre = obtener_prellenado_ventas(guia_id)
    envio_directo = bool(g.get("envio_directo_cedis"))

    def datos(ev_): return (ev_ or {}).get("datos", {}) or {}
    def en(ev_): return (ev_ or {}).get("en", "") or ""

    # Determinar si la guía es editable
    def _es_editable():
        if user.get("rol") not in ("ventas", "admin"):
            return False
        est = g.get("estado")
        if est in ("RECIBIDA_ADMIN", "EN_RUTA", "ENTREGADA", "ANULADA"):
            return False
        tipos_procesados = {e["tipo"] for e in evs if e["tipo"] not in ("creacion", "envio_directo_cedis", "edicion_guia")}
        return len(tipos_procesados) == 0

    editable = _es_editable()
    estado = g.get("estado", "")
    tiene_transporte = any(e.get("tipo") == "entrega_transporte" for e in evs)

    bultos_pre = ""
    if any(pre.get(k) not in (None, "", 0) for k in ("cajas","bolsas","cayvas","sobres","otros","totales")):
        bultos_pre = f"""<div class="subblk">
          <h4>📦 Bultos informados por Ventas (CEDIS confirma/edita)</h4>
          <div class="grid">
            {fila('Cajas (Ventas)', pre.get('cajas'))}
            {fila('Bolsas (Ventas)', pre.get('bolsas'))}
            {fila('Cavas (Ventas)', pre.get('cayvas'))}
            {fila('Sobres (Ventas)', pre.get('sobres'))}
            {fila('Otros (Ventas)', pre.get('otros'))}
            {fila('Totales (Ventas)', pre.get('totales'))}
          </div>
        </div>"""

    blk_ventas_extra = ""
    any_datos_cliente = any(
        str(pre.get(k) or "").strip() != ""
        for k in ("cliente_recibe_nombre",)
    )
    any_datos_transp = any(
        str(pre.get(k) or "").strip() != ""
        for k in ("transportador_nombre", "transportador_cc", "transportador_tel",
                  "transportador_vehiculo", "transportador_placa", "transportador_flete")
    )
    if envio_directo:
        if any_datos_cliente or any_datos_transp:
            blk_ventas_extra = f"""<div class="subblk">
              <h4>🏃 Persona que RETIRA en CEDIS (informados por Ventas · envío directo)</h4>
              {fila('Nombre completo', pre.get('cliente_recibe_nombre'))}
              {fila('Documento / CC', pre.get('transportador_cc'))}
              {fila('Teléfono', pre.get('transportador_tel'))}
              {fila('Vehículo', pre.get('transportador_vehiculo'))}
              {fila('Placa', pre.get('transportador_placa'))}
              {fila('Observación entrega', pre.get('transportador_nombre'))}
            </div>"""
    else:
        if any_datos_cliente:
            blk_ventas_extra = f"""<div class="subblk">
              <h4>🏃 Persona que recibe el pedido (informados por Ventas)</h4>
              {fila('Nombre completo', pre.get('cliente_recibe_nombre'))}
            </div>"""
        if any_datos_transp:
            # Transportador EXTERNO: datos que ya registró Administrativo (antes de entrega_transporte evento)
            firma_admin_prev = obtener_ultima_firma_transportador_admin(int(g["id"]))
            fila_firma = ""
            if firma_admin_prev:
                fila_firma = f'<div class="kv"><span>Firma (capturada por Administrativo)</span><b><img src="{escape(firma_admin_prev)}" class="firma" alt="firma transportador"></b></div>'
            tipo_t = g.get("tipo_transportador") or ""
            blk_ventas_extra = (blk_ventas_extra or "") + f"""<div class="subblk">
              <h4>🚛 Datos transportador {("EXTERNO" if tipo_t=="externo" else "registrados")} · Bodega/Administrativa</h4>
              {fila('Nombre transportador', pre.get('transportador_nombre'))}
              {fila('Documento / CC', pre.get('transportador_cc'))}
              {fila('Teléfono', pre.get('transportador_tel'))}
              {fila('Vehículo', pre.get('transportador_vehiculo'))}
              {fila('Placa', pre.get('transportador_placa'))}
              {fila('Valor flete', pre.get('transportador_flete'))}
              {fila_firma}
            </div>"""
    envio_directo_tag = ""
    if envio_directo:
        envio_directo_tag = """<div class="chip ok">✓ Envío DIRECTO a CEDIS (sin paso por Bodega)</div>"""
    blk_ventas = f"""<section class="card bloque"><h3>1 · VENTAS {envio_directo_tag}</h3>
      {fila('Ciudad y fecha', f"{g.get('ciudad') or ''} · {g.get('creada_en') or ''}")}
      {fila('NIT', g.get('nit') or pre.get('nit') or '—')}
      {fila('Cliente', g.get('cliente'))}
      {fila('Centro de operación', g.get('centro_operacion') or pre.get('centro_operacion') or '—')}
      {fila('Dirección', g.get('direccion'))}
      {fila('Prefijo documento', g.get('prefijo') or pre.get('prefijo') or '—')}
      {fila_raw('N° documentos', f'<span data-docs-chips="{escape(str(g.get("documentos") or ""))}">{escape(str(g.get("documentos") or "—"))}</span>')}
      {fila_raw('Observaciones', f'<span data-docs-chips="{escape(str(g.get("obs_ventas") or ""))}">{escape(str(g.get("obs_ventas") or "—"))}</span>')}
      {fila('Entrega', datos(cre).get('entrega_nombre'))}
      {fila('Fecha/hora entrega', en(cre))}
      {bultos_pre}
      {blk_ventas_extra}
      <div class="kv"><span>Firma</span><b>{img_adj(datos(cre).get('firma_archivo'))}</b></div></section>"""
    blk_adm = ""
    if not envio_directo:
        blk_adm = f"""<section class="card bloque"><h3>2 · ADMINISTRACIÓN</h3>
          {fila('Recibe', datos(adm).get('recibe'))}{fila('Fecha/hora', en(adm))}
          <div class="kv"><span>Firma</span><b>{img_adj(datos(adm).get('firma_archivo'))}</b></div></section>"""
    else:
        blk_adm = """<section class="card bloque bloque-saltado"><h3>2 · ADMINISTRACIÓN <span class="chip info">Saltado (envío directo)</span></h3>
          <p class="nota">Esta guía se envió directamente a CEDIS sin pasar por recepción Bodega.</p></section>"""
    d = datos(ctrl)
    blk_cedis = f"""<section class="card bloque"><h3>3 · CEDIS</h3>
      {fila('Cajas', d.get('cajas'))}{fila('Bolsas', d.get('bolsas'))}{fila('Cavas', d.get('cayvas'))}
      {fila('Sobres', d.get('sobres'))}{fila('Otros', d.get('otros'))}{fila('Totales', d.get('totales'))}
      {fila('Vechículo cumple', d.get('vehiculo_cumple'))}{fila('Observaciones', d.get('obs'))}
      {fila('Fecha/hora', en(ctrl))}
      <div class="kv"><span>Firma legible</span><b>{img_adj(d.get('firma_archivo'))}</b></div></section>"""
    d = datos(trn)
    if not trn and envio_directo:
        blk_trn = """<section class="card bloque bloque-saltado"><h3>4 · TRANSPORTADOR DIRECTO <span class="chip info">Saltado (envío directo · cliente recoge en CEDIS)</span></h3>
          <p class="nota">Flujo envío directo: no hubo transportador. El cliente vino personalmente a CEDIS a recoger su mercancía y la entrega se cerró directamente en el paso 5 (Cliente/Farmacia).</p></section>"""
    elif not trn:
        # Aún no hay evento entrega_transporte -> mostrar DATOS PRE que registró Administrativo (info solo lectura)
        hay_datos_pre = any(
            str(pre.get(k) or "").strip() != ""
            for k in ("transportador_nombre", "transportador_cc", "transportador_tel",
                      "transportador_vehiculo", "transportador_placa", "transportador_flete")
        )
        tipo_t = g.get("tipo_transportador") or ""
        chip_tag = ""
        if tipo_t == "propio":
            chip_tag = '<span class="chip ok">PROPIO · con usuario</span>'
        elif tipo_t == "externo":
            chip_tag = '<span class="chip" style="background:#d97706;color:#fff">EXTERNO · sin usuario</span>'
        info_banner = ""
        if not tipo_t:
            info_banner = '<p class="nota">Esperando a que <b>Administrativo</b> asigne tipo de transportador (propio o externo) y registre sus datos.</p>'
        elif not hay_datos_pre:
            info_banner = '<p class="nota">Datos del transportador aún no registrados por Administrativo. Pendiente de prellenar.</p>'
        if hay_datos_pre:
            firma_admin_prev = obtener_ultima_firma_transportador_admin(int(g["id"]))
            fila_firma = ""
            if firma_admin_prev:
                fila_firma = f'<div class="kv"><span>Firma capturada en Administrativo</span><b><img src="{escape(firma_admin_prev)}" class="firma" alt="firma transportador"></b></div>'
            blk_trn = f"""<section class="card bloque info"><h3>4 · TRANSPORTADOR DIRECTO {chip_tag} <span class="chip info" style="background:#e0e7ff;color:#1e40af">⏳ Pendiente de entrega en CEDIS</span></h3>
              {info_banner}
              <p class="nota">📋 Datos informados por <b>Administrativo</b> (solo lectura). CEDIS confirmará la entrega real de la mercancía en su módulo.</p>
              {fila('Nombre transportador', pre.get('transportador_nombre'))}
              {fila('CC', pre.get('transportador_cc'))}{fila('Tel', pre.get('transportador_tel'))}
              {fila('Vehículo', pre.get('transportador_vehiculo'))}{fila('Placa', pre.get('transportador_placa'))}
              {fila('Valor flete', pre.get('transportador_flete'))}
              {fila_firma}
              <p class="nota" style="margin-top:8px">👉 Una vez CEDIS guarde <b>Entrega a transportador</b>, este bloque se llenará con los datos finales y firma de entrega real.</p></section>"""
        else:
            blk_trn = f"""<section class="card bloque info"><h3>4 · TRANSPORTADOR DIRECTO {chip_tag} <span class="chip info" style="background:#e0e7ff;color:#1e40af">⏳ Pendiente</span></h3>
              {info_banner}</section>"""
    else:
        # Si hay evento entrega_transporte (ya se realizó la entrega en CEDIS)
        blk_trn = f"""<section class="card bloque"><h3>4 · TRANSPORTADOR DIRECTO</h3>
          {fila('Nombre', d.get('nombre'))}{fila('CC', d.get('cc'))}{fila('Tel', d.get('tel'))}
          {fila('Vehículo', d.get('vehiculo'))}{fila('Placa', d.get('placa'))}{fila('Valor flete', d.get('flete'))}
          {fila('Fecha/hora', en(trn))}
          <div class="kv"><span>Firma</span><b>{img_adj(d.get('firma_archivo'))}</b></div></section>"""
    d = datos(cli)
    blk_cli = f"""<section class="card bloque"><h3>5 · CLIENTE / FARMACIA</h3>
      {fila('Recibe', d.get('recibe'))}{fila('Fecha/hora', en(cli))}
      {fila('Observaciones', d.get('obs'))}
      <div class="kv"><span>Firma</span><b>{img_adj(d.get('firma_archivo'))}</b></div>
      <div class="kv"><span>Foto evidencia</span><b>{img_adj(d.get('foto_archivo'), 'foto', 'foto')}</b></div></section>"""

    tl = "".join(
        f"<tr><td>{escape(x.get('en',''))}</td>"
        f"<td>{escape(TIPO_TITULO.get(x.get('tipo',''), x.get('tipo','')))}</td>"
        f"<td>{escape(x.get('usuario') or '')} ({escape(ROL_LABEL.get(x.get('rol'), x.get('rol','')))})</td>"
        f"<td class='dev'>{escape((x.get('dispositivo') or '')[:40])}</td></tr>"
        for x in evs
    )

    # Formulario de edición inline (solo si es editable)
    bloque_editar = ""
    if editable:
        bloque_editar = f"""<section class="card formbox info" id="bloque-editar">
      <h3>✏️ Editar guía <small>(solo antes de ser procesada)</small>
        <button type="button" class="btn mini" id="btn-toggle-editar" style="float:right;margin-left:10px">Mostrar formulario</button>
      </h3>
      <p class="nota">Puedes corregir cualquier error antes de que Administrativa o CEDIS procesen la guía.
      <b>Cada modificación queda registrada como evento de auditoría</b> para trazabilidad futura.</p>
      <form class="form grid" id="form-editar-guia" data-api="/api/guias/{g['id']}/editar" data-redirect="true" style="display:none">
        <label>Ciudad<input name="ciudad" required value="{escape(g.get('ciudad') or '')}"></label>
        <label>Cliente<input name="cliente" required value="{escape(g.get('cliente') or '')}"></label>
        <label class="wide">Dirección<input name="direccion" value="{escape(g.get('direccion') or '')}"></label>
        <label>N° documentos<input name="documentos" value="{escape(g.get('documentos') or '')}" placeholder="FV 20929 - REM 456"></label>
        <label class="wide">Observaciones ventas
          <small class="ayuda">Separa documentos con <b>guion (-)</b></small>
          <textarea name="obs_ventas" rows="3">{escape(g.get('obs_ventas') or '')}</textarea>
        </label>

        <fieldset class="wide"><legend>📦 Bultos · actualizar</legend>
          <div class="bultos-grid">
            <label>N° cajas<input name="cajas" type="number" min="0" value="{int(pre.get('cajas') or 0)}" class="bulto-input" data-bulto></label>
            <label>N° bolsas<input name="bolsas" type="number" min="0" value="{int(pre.get('bolsas') or 0)}" class="bulto-input" data-bulto></label>
            <label>N° cavas<input name="cayvas" type="number" min="0" value="{int(pre.get('cayvas') or 0)}" class="bulto-input" data-bulto></label>
            <label>N° sobres<input name="sobres" type="number" min="0" value="{int(pre.get('sobres') or 0)}" class="bulto-input" data-bulto></label>
            <label>Otros<input name="otros" value="{escape(pre.get('otros') or '')}"></label>
            <label class="total-bultos">Total unidades<input name="totales" type="number" min="0" value="{int(pre.get('totales') or 0)}" readonly data-total-unidades></label>
          </div>
        </fieldset>

        <fieldset class="wide"><legend>🏃 Cliente / Persona que retira o recibe</legend>
          <div class="grid">
            <label class="wide">Nombre completo<input name="cliente_recibe_nombre" value="{escape(pre.get('cliente_recibe_nombre') or '')}"></label>
            <label>Documento / CC<input name="transportador_cc" value="{escape(pre.get('transportador_cc') or '')}"></label>
            <label>Teléfono<input name="transportador_tel" value="{escape(pre.get('transportador_tel') or '')}"></label>
            <label>Vehículo (si aplica)<input name="transportador_vehiculo" value="{escape(pre.get('transportador_vehiculo') or '')}"></label>
            <label>Placa (si aplica)<input name="transportador_placa" value="{escape(pre.get('transportador_placa') or '')}"></label>
            <label>Observación entrega<input name="transportador_nombre" value="{escape(pre.get('transportador_nombre') or '')}"></label>
          </div>
        </fieldset>

        <label>Entrega (quien despacha)<input name="entrega_nombre" value="{escape(datos(cre).get('entrega_nombre') or user.get('nombre') or '')}"></label>

        <label class="wide chk"><input type="checkbox" name="envio_directo_cedis" value="1" {"checked" if envio_directo else ""}>
          <b>🚀 Envío DIRECTO a CEDIS</b> (cambia el flujo sin paso por Bodega; editable solo antes de procesar)</label>

        <button type="submit" class="btn primario wide">💾 Guardar cambios · registrar auditoría</button>
      </form>
    </section>"""

    rol_u = user.get("rol", "")
    puede_generar_token = rol_u in ("ventas", "administrativo", "admin") and estado not in ("ENTREGADA", "ANULADA") and (tiene_transporte or envio_directo)
    puede_asignar_transportador = False
    tipo_transportador_actual = g.get("tipo_transportador") or ""
    transportador_asignado_actual = g.get("transportador_asignado_id") or None

    bloque_compartir = ""
    if puede_generar_token:
        tok_info = obtener_info_token_guia(int(g["id"]))
        # SPEC T5: Banner estado activación link según estado guía.
        activ_link = estado_activacion_link(int(g["id"]))
        banner_activacion = ""
        if activ_link["codigo"] == "OK":  # EN_RUTA
            banner_activacion = f"""<div class="subblk" style="margin-bottom:12px;padding:10px 14px;border-radius:8px;background:#ecfdf5;border-left:4px solid #059669">
<b style="color:#065f46">🟢 Link ACTIVO y listo para enviar al cliente.</b><br>
• La guía ya salió de CEDIS y está en estado <b>EN_RUTA</b>. El cliente puede abrir el link y confirmar la entrega inmediatamente.
</div>"""
        elif activ_link["codigo"] == "NO_ACTIVO":  # CREADA / RECIBIDA_ADMIN / EN_CEDIS
            banner_activacion = f"""<div class="subblk" style="margin-bottom:12px;padding:10px 14px;border-radius:8px;background:#eff6ff;border-left:4px solid #2563eb">
<b style="color:#1e40af">🔵 Link NO ACTIVO · AÚN (no lo envíes aún al cliente).</b><br>
• Estado actual: <b>{escape(str(activ_link.get('estado_guia','-')))}</b><br>
• {escape(str(activ_link.get('motivo','')))}
</div>"""
        host_default = "localhost:8000"
        tok_link_exist = ""
        banner_emitido = ""
        ya_tiene_link = bool(tok_info)
        btn_texto_inicial = "🔗 Ver link emitido" if ya_tiene_link else "🔗 Generar link de confirmación"
        resultado_display = "block" if ya_tiene_link else "none"
        if tok_info:
            t_tok = tok_info.get("token") or ""
            scheme_t = "http"
            tok_link_exist = f"{scheme_t}://{host_default}/firma/{t_tok}"
            usado_txt = (
                "✅ El cliente <b>ya confirmó la entrega</b> (usado el " + escape(str(tok_info.get("usado_en") or "-")) + ")"
                if tok_info.get("usado_en")
                else "⏳ Pendiente que el cliente abra y confirme la recepción"
            )
            banner_emitido = f"""<div class="subblk warning" style="margin-bottom:12px;padding:10px 14px;border-radius:8px;background:#fef3c7;border-left:4px solid #d97706">
<b>🔴 Link de confirmación YA FUE EMITIDO</b><br>
• Fecha emisión: {escape(str(tok_info.get("creado_en") or "-"))}<br>
• Emitido por: <b>{escape(str(tok_info.get("creado_por_nombre") or tok_info.get("creado_por_usuario") or "-"))}</b> (Rol: {escape(str(tok_info.get("creado_rol") or "-"))})<br>
• Estado: {usado_txt}
</div>"""
        bloque_compartir = f"""
    <section class="card formbox info" id="bloque-compartir">
      <h3>🔗 Link de confirmación / firma cliente</h3>
      <p class="nota">Genera un <b>link público único</b> para que el cliente confirme la entrega sin iniciar sesión.
      Puedes compartirlo por <b>WhatsApp</b>, <b>Correo</b> o copiarlo al portapapeles. El link expira en 7 días y es de un solo uso.
      <br><b>Regla SPEC:</b> El link <b>SÓLO se activa para el cliente DESPUÉS</b> de que CEDIS guarde su proceso único (control + entrega a transportador → estado <b>EN_RUTA</b>).</p>
      {banner_activacion}
      {banner_emitido}
      <div class="btns-row" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px 0">
        <button type="button" class="btn primario" id="btn-generar-link" data-id-guia="{g['id']}">{btn_texto_inicial}</button>
      </div>
      <div id="resultado-link" style="display:{resultado_display};margin-top:10px">
        <label class="wide">Link público de confirmación:
          <input type="text" id="link-publico-input" readonly value="{escape(tok_link_exist)}" style="width:100%;background:#f8fafc;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-top:6px;font-family:monospace;font-size:12px">
        </label>
        <div class="btns-row" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
          <button type="button" class="btn" id="btn-copiar-link">📋 Copiar</button>
          <a class="btn" id="btn-whatsapp-link" target="_blank" rel="noopener" href="{escape(tok_link_exist) if ya_tiene_link else '#'}">💬 WhatsApp</a>
          <a class="btn" id="btn-email-link" target="_blank" rel="noopener">📧 Correo</a>
        </div>
      </div>
    </section>
    <script>
    (function(){{
      const btn = document.getElementById('btn-generar-link');
      if (!btn) return;
      const gid = btn.dataset.idGuia;
      const resBox = document.getElementById('resultado-link');
      const inp = document.getElementById('link-publico-input');
      const btnC = document.getElementById('btn-copiar-link');
      const btnW = document.getElementById('btn-whatsapp-link');
      const btnE = document.getElementById('btn-email-link');
      btn.addEventListener('click', async () => {{
        btn.disabled = true; btn.textContent = '⏳ Procesando…';
        try {{
          const r = await fetch(`/api/guias/${{gid}}/generar_token_entrega`, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:'{{}}'}});
          const d = await r.json();
          if (!d || !d.ok) throw new Error((d && d.error) || 'Error generando');
          if (d.ya_emitido) {{
            const em = d.emision || {{}};
            alert('ℹ️ Este link ya había sido generado por ' + (em.nombre_original || em.usuario_original || '-') + ' (Rol: ' + (em.rol_original || '-') + '). Reutilizando el mismo link para evitar doble envío.');
          }}
          inp.value = d.link || '';
          resBox.style.display = 'block';
          btnW.href = d.whatsapp || '#';
          const subj = encodeURIComponent('Confirmación entrega guía No. {escape(str(g.get('consecutivo') or ''))}');
          const body = encodeURIComponent(`Confirme la entrega de su pedido - Guía No. {escape(str(g.get('consecutivo') or ''))}\\n\\n${{d.link||''}}`);
          btnE.href = `mailto:?subject=${{subj}}&body=${{body}}`;
          btn.disabled = false; btn.textContent = '🔗 Ver link emitido';
        }} catch (e) {{ alert('Error: ' + e.message); btn.disabled=false; btn.textContent='🔗 Generar link de confirmación'; }}
      }});
      btnC && btnC.addEventListener('click', async () => {{ try {{ await navigator.clipboard.writeText(inp.value); btnC.textContent='✅ Copiado!'; setTimeout(()=>btnC.textContent='📋 Copiar', 1800); }} catch(e){{alert('No se pudo copiar'); }} }});
    }})();
    </script>
    """

    bloque_asignar_transp = ""
    if puede_asignar_transportador:
        checked_prop = tipo_transportador_actual == "propio"
        checked_ext = tipo_transportador_actual == "externo"
        checked_none = not tipo_transportador_actual
        bloque_asignar_transp = f"""
    <section class="card formbox" id="bloque-asignar-transp">
      <h3>🚛 Asignar tipo de transportador</h3>
      <p class="nota"><b>PROPIO:</b> operario interno con usuario de la empresa (tiene login). <b>EXTERNO:</b> persona sin usuario (firma recogida por Administración o CEDIS).</p>
      <form class="form grid" data-api="/api/guias/{g['id']}/asignar_transportador" data-redirect="true">
        <fieldset class="wide">
          <legend>Selecciona el tipo:</legend>
          <label class="chk"><input type="radio" name="tipo" value="propio" {"checked" if checked_prop else ""} onchange="document.getElementById('wrap-transp-propios').style.display=this.checked?'block':'none'"> 🟢 Transportador PROPIO (con usuario)</label>
          <label class="chk"><input type="radio" name="tipo" value="externo" {"checked" if checked_ext else ""} onchange="document.getElementById('wrap-transp-propios').style.display='none'"> 🟡 Transportador EXTERNO (sin usuario)</label>
        </fieldset>
        <div id="wrap-transp-propios" style="display:{'block' if checked_prop else 'none'}; margin-top: 6px" class="wide">
          <label>Selecciona el transportador propio asignado:
            <select name="transportador_asignado_id" id="select-transp-propios" style="width:100%;margin-top:6px;padding:8px;border-radius:8px;border:1px solid #cbd5e1">
              <option value="">-- Cargando transportadores... --</option>
            </select>
          </label>
        </div>
        <button class="btn primario wide">💾 Guardar asignación</button>
      </form>
    </section>
    <script>
    (function(){{
      const sel = document.getElementById('select-transp-propios');
      if (sel) {{
        fetch('/api/usuarios/rol/transportador').then(r=>r.json()).then(d=>{{
          if (d && d.ok && d.transportadores) {{
            const prev = "{escape(str(transportador_asignado_actual or ''))}";
            sel.innerHTML = '<option value="">-- Selecciona un transportador --</option>' +
              d.transportadores.map(t=>`<option value="${{t.id}}" ${{prev==String(t.id)?'selected':''}}>${{t.nombre}} (${{t.usuario}})</option>`).join('');
          }}
        }}).catch(e=>{{ sel.innerHTML='<option>Error cargando</option>'; }});
      }}
    }})();
    </script>
    """

    bloque_tipo_transp_info = ""
    if tipo_transportador_actual:
        from guias_coodescor.services.guias_service import obtener_usuario_transportador_por_id as _outi
        tinfo_nombre = ""
        if transportador_asignado_actual:
            _tu = _outi(int(transportador_asignado_actual))
            if _tu: tinfo_nombre = f" · {escape(_tu.get('nombre') or '')} ({escape(_tu.get('usuario') or '')})"
        badge = "<span class='chip ok'>PROPIO</span>" if tipo_transportador_actual == "propio" else "<span class='chip' style='background:#d97706'>EXTERNO</span>"
        bloque_tipo_transp_info = f"""<div class="chip-row" style="margin-bottom:12px">Tipo transportador: {badge}{escape(tinfo_nombre)}</div>"""

    cuerpo = f"""
    <div class="cabguia"><h2>Guía No. {g.get('consecutivo')}</h2>{estado_chip(g)}
      <a class="btn" href="/guia/{g['id']}/imprimir" target="_blank">🖨️ Imprimir / PDF</a>
      <a class="btn" href="/tablero">Volver</a></div>
    {stepper(g)}
    {bloque_editar}
    {bloque_compartir}
    {bloque_tipo_transp_info}
    <div class="bloques">{blk_ventas}{blk_adm}{blk_cedis}{blk_trn}{blk_cli}</div>
    <section class="card"><h3>🔎 Trazabilidad · código {escape(cod)}</h3>
      {f'<div class="qr">{qr}</div>' if qr else ''}
      <table class="tabla"><tr><th>Fecha/hora</th><th>Evento</th><th>Usuario</th><th>Dispositivo</th></tr>{tl}</table>
    </section>
    {_formulario_accion(g, user)}"""
    return page(f"Guía {g.get('consecutivo')}", cuerpo, user)


def vista_firma_publica(token_info: dict, guia: dict | None) -> str:
    """Vista PÚBLICA (sin login) para que el cliente confirme entrega vía link token.
    token_info: dict con id, guia_id, token, creado_en, creado_ip, expira, usado_en, usado_ip.
    guia: dict completo de la guía (obtenido antes de renderizar)."""
    if not guia or not token_info:
        cuerpo = """<section class="card">
        <h2>⚠️ Link no válido</h2>
        <p class="sin">El link de confirmación es inválido, ha expirado o ya fue usado.
        Por favor solicita un nuevo link al área de ventas o administrativo.</p>
        <a class="btn primario" href="/login">Volver al inicio</a></section>"""
        return page("Link inválido", cuerpo, user=None)

    from guias_coodescor.services.eventos_service import listar_eventos as _lev_pub
    evs_pub = _lev_pub(int(guia["id"]))
    ev_pub = {x["tipo"]: x for x in evs_pub}
    cli_pub = ev_pub.get("entrega_cliente")
    pre_pub = obtener_prellenado_ventas(int(guia["id"]))

    ya_entregada = guia.get("estado") == "ENTREGADA" or bool(token_info.get("usado_en")) or bool(cli_pub)
    token = str(token_info.get("token") or "")

    if ya_entregada:
        d = (cli_pub or {}).get("datos", {}) or {}
        cuerpo = f"""<section class="card">
          <h2>✅ ¡Entrega confirmada! Gracias</h2>
          <p class="nota">Esta guía ya fue marcada como ENTREGADA. Si tienes novedades contacta a Coodescor.</p>
          <div class="subblk">
            <h4>Resumen de la entrega</h4>
            {fila('Guía N°', guia.get('consecutivo'))}
            {fila('Cliente', guia.get('cliente'))}
            {fila('Recibió', d.get('recibe') or pre_pub.get('cliente_recibe_nombre') or 'Confirmado')}
            {fila('Fecha/hora', (cli_pub or {}).get('en') or token_info.get('usado_en') or '')}
            {fila('Observaciones', d.get('obs') or '')}
          </div>
          <a class="btn primario" href="/login">Volver</a>
        </section>"""
        return page("Entrega confirmada", cuerpo, user=None)

    nombre_p = pre_pub.get("cliente_recibe_nombre") or ""
    doc_p = pre_pub.get("transportador_cc") or ""
    tel_p = pre_pub.get("transportador_tel") or ""
    cuerpo = f"""<section class="card">
      <h2>📦 Confirmar entrega · Guía N° {escape(str(guia.get('consecutivo') or ''))}</h2>
      <p class="nota">Por favor confirma la recepción de la mercancía.
      <b>Debes firmar o adjuntar una foto</b> para dar por cerrada la entrega.
      Esta acción es de un solo uso y queda registrada.</p>

      <div class="subblk info-preview">
        <h4>👤 Datos de la guía</h4>
        <div class="grid">
          {fila('Cliente', guia.get('cliente'))}
          {fila('Dirección', guia.get('direccion'))}
          {fila('Ciudad', guia.get('ciudad'))}
          {fila('N° documentos', guia.get('documentos'))}
          {fila('Observaciones', guia.get('obs_ventas'))}
          {fila('Persona que recibe (informado)', nombre_p)}
          {fila('Documento (informado)', doc_p)}
          {fila('Teléfono (informado)', tel_p)}
        </div>
      </div>

      <section class="card formbox" style="margin-top:20px">
        <h3>✍️ Firma de confirmación de entrega</h3>
        <form class="form grid" id="form-firma-publica" data-api="/api/firma_publica/{escape(token)}" data-redirect="true">
          <label class="wide">Nombre completo de QUIÉN RECIBE Y FIRMA<input name="recibe" required value="{escape(nombre_p)}" placeholder="Tu nombre completo"></label>
          <div class="sigbox wide"><span>Firma (dibuja con el dedo o mouse):</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar firma</button></div>
          <label class="wide">📷 Foto evidencia (opcional si hay firma · obligatorio si no puedes firmar)
            <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
          <label class="wide">Observaciones (opcional)<textarea name="obs" rows="2" placeholder="Ej: Todo en orden, recibi 4 cajas, 2 cavas"></textarea></label>
          <button class="btn primario wide" data-confirm="¿Confirmas la recepción de la mercancía? Esta acción cierra la guía y no puede deshacerse.">✅ Confirmar entrega · Cerrar guía</button>
          <p class="nota">Al presionar confirmas <b>explícitamente</b> haber recibido la mercancía en buen estado.</p>
        </form>
      </section>
    </section>"""
    return page(f"Confirmar entrega guía {guia.get('consecutivo')}", cuerpo, user=None)


def vista_imprimir_guia(guia_id: int, user: dict) -> str:
    g = obtener_guia(guia_id)
    if not g:
        return page("Guía", "<p class='sin'>Guía no encontrada.</p>", user)
    evs = listar_eventos(guia_id)
    ev = {x["tipo"]: x for x in evs}
    pre = obtener_prellenado_ventas(guia_id)
    envio_directo = bool(g.get("envio_directo_cedis"))
    tiene_entrega_transporte = bool(ev.get("entrega_transporte"))

    def dd(t): return (ev.get(t) or {}).get("datos", {}) or {}
    def en(t): return (ev.get(t) or {}).get("en", "") or ""
    def img(t, k):
        r = dd(t).get(k + "_archivo")
        return f'<img class="mini-firma" src="/static_file/{escape(r)}">' if r else "<span class='sin'>—</span>"

    empresa = escape(obtener_config("empresa", "Coodescor"))
    pie = escape(obtener_config("pie", ""))
    cod = generar_codigo_verificacion(g)
    estado_txt = escape(ESTADOS.get(g.get("estado"), (g.get("estado"), ""))[0])

    transportador_html = ""
    if tiene_entrega_transporte:
        transportador_html = f"""
        <tr><th colspan="4">TRANSPORTADOR DIRECTO</th></tr>
        <tr><td>Nombre</td><td>{escape(dd('entrega_transporte').get('nombre') or '')}</td>
            <td>CC / Tel</td><td>{escape(dd('entrega_transporte').get('cc') or '')} / {escape(dd('entrega_transporte').get('tel') or '')}</td></tr>
        <tr><td>Vehículo / Placa</td><td>{escape(dd('entrega_transporte').get('vehiculo') or '')} / {escape(dd('entrega_transporte').get('placa') or '')}</td>
            <td>Flete</td><td>{escape(dd('entrega_transporte').get('flete') or '')}</td></tr>
        <tr><td>Fecha/hora</td><td>{escape(en('entrega_transporte'))}</td>
            <td>Firma</td><td>{img('entrega_transporte','firma')}</td></tr>
        """
    elif envio_directo:
        transportador_html = """
        <tr><th colspan="4">TRANSPORTADOR DIRECTO</th></tr>
        <tr><td colspan="4" class="empty-row">No aplica · Envío directo: cliente recoge personalmente en CEDIS (sin transportador)</td></tr>
        """
    else:
        transportador_html = """
        <tr><th colspan="4">TRANSPORTADOR DIRECTO</th></tr>
        <tr><td colspan="4" class="empty-row">Pendiente · entrega al transportador aún no realizada</td></tr>
        """

    admin_html = ""
    if envio_directo:
        admin_html = """<tr><th colspan="4">ADMINISTRACIÓN</th></tr>
        <tr><td colspan="4" class="empty-row">Saltado por envío directo a CEDIS</td></tr>"""
    else:
        admin_html = f"""<tr><th colspan="4">ADMINISTRACIÓN</th></tr>
        <tr><td>Recibe</td><td>{escape(dd('recepcion_admin').get('recibe') or '')} · {escape(en('recepcion_admin'))}</td>
            <td>Firma</td><td>{img('recepcion_admin','firma')}</td></tr>"""

    cuerpo = f"""<style>
      @page {{ size: A4 portrait; margin: 8mm; }}
      body {{ background: #e5e7eb; margin: 0; }}
      .acta-print {{ width: 100%; max-width: 760px; margin: 0 auto; background: #f7f7f7; border: 1px solid #cbd5e1; box-shadow: 0 8px 24px rgba(15,23,42,.08); padding: 0; }}
      .acta-header {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 20px 10px; background: #f7f7f7; border-bottom: 2px solid #dbe2ec; }}
      .marca {{ display: flex; align-items: center; font-weight: 700; color: #1f2937; gap: 8px; }}
      .marca .logo-circle {{ width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg,#0f172a,#2563eb); color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 14px; }}
      .titulo {{ text-align: center; font-weight: 700; font-size: 17px; letter-spacing: .2px; }}
      .consecutivo {{ border: 2px solid #1d4ed8; color: #1d4ed8; font-weight: 800; padding: 6px 12px; border-radius: 10px; min-width: 120px; text-align: center; }}
      .subheader {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; padding: 8px 20px 18px; background: #f7f7f7; }}
      .subheader .small {{ font-size: 10px; color: #4b5563; text-transform: uppercase; letter-spacing: .8px; }}
      .acta-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
      .acta-table th {{ background: #1d4ed8; color: white; text-align: left; padding: 8px 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }}
      .acta-table td {{ border: 1px solid #dbe2ec; padding: 7px 8px; vertical-align: top; background: white; color: #0f172a; }}
      .acta-table td:first-child {{ width: 28%; font-weight: 700; background: #f8fafc; }}
      .acta-table td.empty-row {{ background: #f3f4f6; color: #475569; font-style: italic; }}
      .acta-footer {{ display: flex; justify-content: space-between; gap: 8px; padding: 12px 18px 18px; font-size: 11px; color: #475569; background: #f7f7f7; }}
      .mini-firma {{ max-width: 140px; max-height: 52px; border: 1px solid #cbd5e1; border-radius: 6px; }}
      @media print {{ body {{ background: white; }} .acta-print {{ box-shadow: none; border: none; max-width: none; }} }}
    </style>
    <div class="acta-print">
      <div class="acta-header">
        <div class="marca">
          <span class="logo-circle">C</span>
          <div>
            <div style="font-size: 16px;">Coodescor</div>
            <div style="font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.8px;">Transportes y logística</div>
          </div>
        </div>
        <div class="titulo">ACTA DE ENTREGA DE TRANSPORTE DE MERCANCÍAS</div>
        <div class="consecutivo">No. {g.get('consecutivo')}</div>
      </div>
      <div class="subheader">
        <div class="small">{empresa}</div>
        <div class="small">Estado: {estado_txt}</div>
      </div>
      <table class="acta-table">
        <tr><th colspan="4">VENTAS</th></tr>
        <tr>
          <td>Ciudad y fecha</td>
          <td>{escape(g.get('ciudad') or '')} · {escape(g.get('creada_en') or '')}</td>
          <td>Cliente</td>
          <td>{escape(g.get('cliente') or '')}</td>
        </tr>
        <tr>
          <td>NIT</td>
          <td>{escape(g.get('nit') or pre.get('nit') or '')}</td>
          <td>Centro de operación</td>
          <td>{escape(g.get('centro_operacion') or pre.get('centro_operacion') or '')}</td>
        </tr>
        <tr>
          <td>Dirección</td>
          <td>{escape(g.get('direccion') or '')}</td>
          <td>Prefijo · N° de documentos</td>
          <td><b>{escape(g.get('prefijo') or pre.get('prefijo') or '')}</b> · {escape(g.get('documentos') or '')}</td>
        </tr>
        <tr>
          <td>Observaciones</td>
          <td colspan="3">{escape(g.get('obs_ventas') or '')}</td>
        </tr>
        <tr>
          <td>Entrega</td>
          <td>{escape(dd('creacion').get('entrega_nombre') or '')}</td>
          <td>Fecha y hora</td>
          <td>{escape(en('creacion'))}</td>
        </tr>
        <tr>
          <td>Firma</td>
          <td colspan="3">{img('creacion','firma')}</td>
        </tr>
        {admin_html}
        <tr><th colspan="4">CEDIS</th></tr>
        <tr>
          <td>Cajas / Bolsas / Cavas / Sobres</td>
          <td>{escape(str(dd('control_cedis').get('cajas') or '0'))} / {escape(str(dd('control_cedis').get('bolsas') or '0'))} / {escape(str(dd('control_cedis').get('cayvas') or '0'))} / {escape(str(dd('control_cedis').get('sobres') or '0'))}</td>
          <td>Otros / Totales</td>
          <td>{escape(str(dd('control_cedis').get('otros') or ''))} / {escape(str(dd('control_cedis').get('totales') or '0'))}</td>
        </tr>
        <tr>
          <td>Condiciones vehículo</td>
          <td>{escape(dd('control_cedis').get('vehiculo_cumple') or '')}</td>
          <td>Fecha / hora</td>
          <td>{escape(en('control_cedis'))}</td>
        </tr>
        <tr>
          <td>Observaciones</td>
          <td colspan="2">{escape(dd('control_cedis').get('obs') or '')}</td>
          <td>Firma legible {img('control_cedis','firma')}</td>
        </tr>
        {transportador_html}
        <tr><th colspan="4">CLIENTE / FARMACIA</th></tr>
        <tr>
          <td>Recibe</td>
          <td>{escape(dd('entrega_cliente').get('recibe') or '')}</td>
          <td>Fecha / hora</td>
          <td>{escape(en('entrega_cliente'))}</td>
        </tr>
        <tr>
          <td>Firma</td>
          <td>{img('entrega_cliente','firma')}</td>
          <td>Foto evidencia</td>
          <td>{img('entrega_cliente','foto')}</td>
        </tr>
        <tr>
          <td>Observaciones</td>
          <td colspan="3">{escape(dd('entrega_cliente').get('obs') or '')}</td>
        </tr>
      </table>
      <div class="acta-footer">
        <span>Código: {escape(cod)}</span>
        <span>{pie}</span>
      </div>
    </div>
    <script>window.onload=function(){{ setTimeout(function(){{ window.print(); }}, 350); }};</script>
    """
    return page(f"Guía {g.get('consecutivo')} imprimir", cuerpo, user)
