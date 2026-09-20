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
)
from guias_coodescor.web.views.base import (
    escape,
    estado_chip,
    fila,
    img_adj,
    lista_guias,
    page,
    stepper,
)


def _formulario_accion(g: dict, user: dict) -> str:
    rol = user.get("rol", "")
    estado = g.get("estado", "")
    pre = obtener_prellenado_ventas(int(g["id"]))
    if rol in ("administrativo", "admin") and estado == "CREADA":
        return f"""<section class="card formbox"><h3>🛡️ Recepción Bodega / Administrativa</h3>
        <form class="form" data-api="/api/guias/{g['id']}/recepcion_admin" data-redirect="true">
          <label>Recibe<input name="recibe" required value="{escape(user.get('nombre'))}"></label>
          <div class="sigbox"><span>Firma de recepción:</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <button class="btn primario">Firmar recepción</button></form></section>"""
    if rol == "cedis" and estado in ("RECIBIDA_ADMIN", "EN_CEDIS"):
        # control_cedis: acepta ambos estados (flujo normal o directo)
        return f"""<section class="card formbox"><h3>📦 Control CEDIS · bultos y vehículo <small>(datos pre-cargados desde Ventas, confirme o corrija)</small></h3>
        <form class="form grid" data-api="/api/guias/{g['id']}/control_cedis" data-redirect="true">
          <label>N° cajas<input name="cajas" type="number" min="0" value="{int(pre.get('cajas') or 0)}"></label>
          <label>N° bolsas<input name="bolsas" type="number" min="0" value="{int(pre.get('bolsas') or 0)}"></label>
          <label>N° cayvas<input name="cayvas" type="number" min="0" value="{int(pre.get('cayvas') or 0)}"></label>
          <label>N° sobres<input name="sobres" type="number" min="0" value="{int(pre.get('sobres') or 0)}"></label>
          <label>Otros<input name="otros" placeholder="…" value="{escape(pre.get('otros') or '')}"></label>
          <label>Totales<input name="totales" type="number" min="0" value="{int(pre.get('totales') or 0)}"></label>
          <label>Código escaneado (lector)<input name="scan" placeholder="opcional, lector USB"></label>
          <fieldset class="wide"><legend>Condiciones del vehículo</legend>
            <label class="chk"><input type="radio" name="vehiculo_cumple" value="si" checked> Cumple</label>
            <label class="chk"><input type="radio" name="vehiculo_cumple" value="no"> No cumple</label>
          </fieldset>
          <label class="wide">Observaciones<textarea name="obs" rows="2"></textarea></label>
          <div class="sigbox wide"><span>Firma legible CEDIS:</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <button class="btn primario wide">Guardar control</button></form></section>"""
    if rol == "transportador" and estado == "EN_CEDIS":
        return f"""<section class="card formbox"><h3>🚚 Entrega al transportador</h3>
        <p class="nota">Los campos prellenados desde Ventas se muestran aquí; edítelos si cambian.</p>
        <form class="form grid" data-api="/api/guias/{g['id']}/entrega_transporte" data-redirect="true">
          <label class="wide">Nombre transportador<input name="nombre" required value="{escape(pre.get('transportador_nombre') or '')}" placeholder="D. Almanza"></label>
          <label>CC<input name="cc" value="{escape(pre.get('transportador_cc') or '')}" placeholder="77206393"></label>
          <label>Tel<input name="tel" value="{escape(pre.get('transportador_tel') or '')}" placeholder="300…"></label>
          <label>Vehículo<input name="vehiculo" value="{escape(pre.get('transportador_vehiculo') or '')}" placeholder="camión / moto…"></label>
          <label>Placa<input name="placa" value="{escape(pre.get('transportador_placa') or '')}" placeholder="ABC123"></label>
          <label>Valor flete<input name="flete" value="{escape(pre.get('transportador_flete') or '')}" placeholder="90.000"></label>
          <div class="sigbox wide"><span>Firma del transportador:</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <button class="btn primario wide">Registrar entrega al transportador</button></form></section>"""
    if rol == "transportador" and estado == "EN_RUTA":
        return f"""<section class="card formbox"><h3>✅ Entrega al cliente / farmacia</h3>
        <p class="nota">El nombre de quien recibe fue prellenado desde Ventas si lo marcó; confirmar o corregir.
        <b>La firma de quién recibe la ejecuta el transportador</b>, o bien se solicita al imprimir la guía.</p>
        <form class="form grid" data-api="/api/guias/{g['id']}/entrega_cliente" data-redirect="true">
          <label class="wide">Recibe<input name="recibe" required value="{escape(pre.get('cliente_recibe_nombre') or '')}" placeholder="Nombre de quien recibe"></label>
          <div class="sigbox wide"><span>Firma del cliente (o foto si no puede firmar):</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <label class="wide">📷 Foto evidencia (opcional si hay firma)
            <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
          <label class="wide">Observaciones<textarea name="obs" rows="2"></textarea></label>
          <button class="btn primario wide">Confirmar entrega</button></form>
          <p class="nota">Se exige firma <b>o</b> foto para cerrar la guía.</p></section>"""
    if rol == "cedis" and estado in ("EN_CEDIS", "EN_RUTA"):
        from guias_coodescor.services.eventos_service import listar_eventos as _lev
        tiene_control = any(e.get("tipo") == "control_cedis" for e in _lev(int(g["id"])))
        tiene_transporte = any(e.get("tipo") == "entrega_transporte" for e in _lev(int(g["id"])))

        if not tiene_transporte and estado == "EN_CEDIS":
            return f"""<section class="card formbox"><h3>✅ Entrega al cliente / farmacia</h3>
        <p class="nota">CEDIS puede cerrar la entrega directamente desde aquí cuando la guía va sin transportador.
        <b>Si aplica, la entrega se confirma con firma o foto sin pasar por transportador.</b></p>
        <form class="form grid" data-api="/api/guias/{g['id']}/entrega_cliente" data-redirect="true">
          <label class="wide">Recibe<input name="recibe" required value="{escape(pre.get('cliente_recibe_nombre') or '')}" placeholder="Nombre de quien recibe"></label>
          <div class="sigbox wide"><span>Firma del cliente (o foto si no puede firmar):</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <label class="wide">📷 Foto evidencia (opcional si hay firma)
            <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
          <label class="wide">Observaciones<textarea name="obs" rows="2"></textarea></label>
          <button class="btn primario wide">Confirmar entrega directa</button></form>
          <p class="nota">Se exige firma <b>o</b> foto para cerrar la guía.</p></section>"""

        if estado == "EN_RUTA":
            return f"""<section class="card formbox"><h3>✅ Entrega al cliente / farmacia</h3>
        <p class="nota">El nombre de quien recibe fue prellenado desde Ventas si lo marcó; confirmar o corregir.
        <b>La firma de quién recibe la ejecuta CEDIS / transportador</b>, o bien se solicita al imprimir la guía.</p>
        <form class="form grid" data-api="/api/guias/{g['id']}/entrega_cliente" data-redirect="true">
          <label class="wide">Recibe<input name="recibe" required value="{escape(pre.get('cliente_recibe_nombre') or '')}" placeholder="Nombre de quien recibe"></label>
          <div class="sigbox wide"><span>Firma del cliente (o foto si no puede firmar):</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <label class="wide">📷 Foto evidencia (opcional si hay firma)
            <input type="file" accept="image/*" capture="environment" data-foto="foto"></label>
          <label class="wide">Observaciones<textarea name="obs" rows="2"></textarea></label>
          <button class="btn primario wide">Confirmar entrega</button></form>
          <p class="nota">Se exige firma <b>o</b> foto para cerrar la guía.</p></section>"""

        if tiene_control and not tiene_transporte:
            return f"""<section class="card formbox"><h3>🚚 Entrega al transportador directo</h3>
        <p class="nota">Los campos prellenados desde Ventas se muestran aquí; edítelos si cambian.</p>
        <form class="form grid" data-api="/api/guias/{g['id']}/entrega_transporte" data-redirect="true">
          <label class="wide">Nombre transportador<input name="nombre" required value="{escape(pre.get('transportador_nombre') or '')}" placeholder="D. Almanza"></label>
          <label>CC<input name="cc" value="{escape(pre.get('transportador_cc') or '')}" placeholder="77206393"></label>
          <label>Tel<input name="tel" value="{escape(pre.get('transportador_tel') or '')}" placeholder="300…"></label>
          <label>Vehículo<input name="vehiculo" value="{escape(pre.get('transportador_vehiculo') or '')}" placeholder="camión / moto…"></label>
          <label>Placa<input name="placa" value="{escape(pre.get('transportador_placa') or '')}" placeholder="ABC123"></label>
          <label>Valor flete<input name="flete" value="{escape(pre.get('transportador_flete') or '')}" placeholder="90.000"></label>
          <div class="sigbox wide"><span>Firma del transportador:</span>
            <canvas class="sig" data-name="firma" width="600" height="220"></canvas>
            <button type="button" class="btn mini" data-limpiar>Limpiar</button></div>
          <button class="btn primario wide">Registrar entrega al transportador</button></form></section>"""
    if rol == "admin" and estado not in ("ENTREGADA", "ANULADA"):
        return f"""<section class="card formbox danger"><h3>⚠️ Anular guía</h3>
        <form class="form" data-api="/api/guias/{g['id']}/anular" data-redirect="true" data-confirm="¿Anular definitivamente esta guía?">
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
      <label>Ciudad<input name="ciudad" required placeholder="Montería" list="lista-ciudades"></label>
      <datalist id="lista-ciudades">
        <option value="Montería"><option value="Cereté"><option value="Sahagún">
        <option value="Lorica"><option value="Planeta Rica"><option value="Montelíbano">
      </datalist>
      <label>Cliente<input name="cliente" required placeholder="Aristo Farmacéutica SAS" list="lista-clientes-vta" id="input-cliente"></label>
      <datalist id="lista-clientes-vta"></datalist>
      <label class="wide">Dirección<input name="direccion" id="input-direccion" placeholder="Cl 27 # 10-23"></label>
      <label>N° de documentos<input name="documentos" placeholder="FV 20929"></label>
      <label class="wide">Observaciones ventas<textarea name="obs_ventas" rows="2"></textarea></label>

      <fieldset class="wide bultos-ventas"><legend>� Bultos · informados por Ventas (CEDIS confirmará/editará)</legend>
        <div class="grid">
          <label>N° cajas<input name="cajas" type="number" min="0" value="0"></label>
          <label>N° bolsas<input name="bolsas" type="number" min="0" value="0"></label>
          <label>N° cayvas<input name="cayvas" type="number" min="0" value="0"></label>
          <label>N° sobres<input name="sobres" type="number" min="0" value="0"></label>
          <label>Otros (detalle)<input name="otros" placeholder="…"></label>
          <label>Total unidades<input name="totales" type="number" min="0" value="0"></label>
        </div>
      </fieldset>

      <fieldset class="wide"><legend>� Datos del transportador (opcional, CEDIS podrá editar después)</legend>
        <div class="grid">
          <label class="wide">Nombre<input name="transportador_nombre" placeholder="D. Almanza"></label>
          <label>CC<input name="transportador_cc" placeholder="cédula"></label>
          <label>Tel<input name="transportador_tel" placeholder="300…"></label>
          <label>Vehículo<input name="transportador_vehiculo" placeholder="camión / moto"></label>
          <label>Placa<input name="transportador_placa" placeholder="ABC123"></label>
          <label>Valor flete<input name="transportador_flete" placeholder="90.000"></label>
        </div>
      </fieldset>

      <fieldset class="wide" id="bloque-cliente-recibe"><legend>🏁 Persona que recibe en el cliente (CEDIS lo confirma)</legend>
        <label>Nombre de quien recibe<input name="cliente_recibe_nombre" id="input-recibe" placeholder="Contacto de la farmacia"></label>
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

    bultos_pre = ""
    if any(pre.get(k) not in (None, "", 0) for k in ("cajas","bolsas","cayvas","sobres","otros","totales")):
        bultos_pre = f"""<div class="subblk">
          <h4>📦 Bultos informados por Ventas (CEDIS confirma/edita)</h4>
          <div class="grid">
            {fila('Cajas (Ventas)', pre.get('cajas'))}
            {fila('Bolsas (Ventas)', pre.get('bolsas'))}
            {fila('Cayvas (Ventas)', pre.get('cayvas'))}
            {fila('Sobres (Ventas)', pre.get('sobres'))}
            {fila('Otros (Ventas)', pre.get('otros'))}
            {fila('Totales (Ventas)', pre.get('totales'))}
          </div>
        </div>"""

    blk_ventas_extra = ""
    if pre.get("transportador_nombre") or pre.get("cliente_recibe_nombre"):
        blk_ventas_extra = f"""<div class="subblk">
          <h4>Datos pre-cargados desde Ventas</h4>
          {fila('Transportador', pre.get('transportador_nombre'))}
          {fila('CC transportador', pre.get('transportador_cc'))}
          {fila('Tel transportador', pre.get('transportador_tel'))}
          {fila('Vehículo', pre.get('transportador_vehiculo'))}
          {fila('Placa', pre.get('transportador_placa'))}
          {fila('Valor flete', pre.get('transportador_flete'))}
          {fila('Recibe en cliente', pre.get('cliente_recibe_nombre'))}
        </div>"""
    envio_directo_tag = ""
    if envio_directo:
        envio_directo_tag = """<div class="chip ok">✓ Envío DIRECTO a CEDIS (sin paso por Bodega)</div>"""
    blk_ventas = f"""<section class="card bloque"><h3>1 · VENTAS {envio_directo_tag}</h3>
      {fila('Ciudad y fecha', f"{g.get('ciudad') or ''} · {g.get('creada_en') or ''}")}{fila('Cliente', g.get('cliente'))}
      {fila('Dirección', g.get('direccion'))}{fila('N° documentos', g.get('documentos'))}
      {fila('Observaciones', g.get('obs_ventas'))}
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
      {fila('Cajas', d.get('cajas'))}{fila('Bolsas', d.get('bolsas'))}{fila('Cayvas', d.get('cayvas'))}
      {fila('Sobres', d.get('sobres'))}{fila('Otros', d.get('otros'))}{fila('Totales', d.get('totales'))}
      {fila('Vechículo cumple', d.get('vehiculo_cumple'))}{fila('Observaciones', d.get('obs'))}
      {fila('Fecha/hora', en(ctrl))}
      <div class="kv"><span>Firma legible</span><b>{img_adj(d.get('firma_archivo'))}</b></div></section>"""
    d = datos(trn)
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
        <label>N° documentos<input name="documentos" value="{escape(g.get('documentos') or '')}"></label>
        <label class="wide">Observaciones ventas<textarea name="obs_ventas" rows="2">{escape(g.get('obs_ventas') or '')}</textarea></label>

        <fieldset class="wide"><legend>📦 Bultos · actualizar</legend>
          <div class="grid">
            <label>N° cajas<input name="cajas" type="number" min="0" value="{int(pre.get('cajas') or 0)}"></label>
            <label>N° bolsas<input name="bolsas" type="number" min="0" value="{int(pre.get('bolsas') or 0)}"></label>
            <label>N° cayvas<input name="cayvas" type="number" min="0" value="{int(pre.get('cayvas') or 0)}"></label>
            <label>N° sobres<input name="sobres" type="number" min="0" value="{int(pre.get('sobres') or 0)}"></label>
            <label>Otros<input name="otros" value="{escape(pre.get('otros') or '')}"></label>
            <label>Total unidades<input name="totales" type="number" min="0" value="{int(pre.get('totales') or 0)}"></label>
          </div>
        </fieldset>

        <fieldset class="wide"><legend>🚚 Datos del transportador</legend>
          <div class="grid">
            <label class="wide">Nombre<input name="transportador_nombre" value="{escape(pre.get('transportador_nombre') or '')}"></label>
            <label>CC<input name="transportador_cc" value="{escape(pre.get('transportador_cc') or '')}"></label>
            <label>Tel<input name="transportador_tel" value="{escape(pre.get('transportador_tel') or '')}"></label>
            <label>Vehículo<input name="transportador_vehiculo" value="{escape(pre.get('transportador_vehiculo') or '')}"></label>
            <label>Placa<input name="transportador_placa" value="{escape(pre.get('transportador_placa') or '')}"></label>
            <label>Valor flete<input name="transportador_flete" value="{escape(pre.get('transportador_flete') or '')}"></label>
          </div>
        </fieldset>

        <fieldset class="wide"><legend>🏁 Persona que recibe en cliente</legend>
          <label>Nombre de quien recibe<input name="cliente_recibe_nombre" value="{escape(pre.get('cliente_recibe_nombre') or '')}"></label>
        </fieldset>

        <label>Entrega (quien despacha)<input name="entrega_nombre" value="{escape(datos(cre).get('entrega_nombre') or user.get('nombre') or '')}"></label>

        <label class="wide chk"><input type="checkbox" name="envio_directo_cedis" value="1" {"checked" if envio_directo else ""}>
          <b>🚀 Envío DIRECTO a CEDIS</b> (cambia el flujo sin paso por Bodega; editable solo antes de procesar)</label>

        <button type="submit" class="btn primario wide">💾 Guardar cambios · registrar auditoría</button>
      </form>
    </section>"""

    cuerpo = f"""
    <div class="cabguia"><h2>Guía No. {g.get('consecutivo')}</h2>{estado_chip(g)}
      <a class="btn" href="/guia/{g['id']}/imprimir" target="_blank">🖨️ Imprimir / PDF</a>
      <a class="btn" href="/tablero">Volver</a></div>
    {stepper(g)}
    {bloque_editar}
    <div class="bloques">{blk_ventas}{blk_adm}{blk_cedis}{blk_trn}{blk_cli}</div>
    <section class="card"><h3>🔎 Trazabilidad · código {escape(cod)}</h3>
      {f'<div class="qr">{qr}</div>' if qr else ''}
      <table class="tabla"><tr><th>Fecha/hora</th><th>Evento</th><th>Usuario</th><th>Dispositivo</th></tr>{tl}</table>
    </section>
    {_formulario_accion(g, user)}"""
    return page(f"Guía {g.get('consecutivo')}", cuerpo, user)


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
    else:
        transportador_html = """
        <tr><th colspan="4">TRANSPORTADOR DIRECTO</th></tr>
        <tr><td colspan="4" class="empty-row">No aplica · entrega directa desde CEDIS al cliente</td></tr>
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
          <td>Dirección</td>
          <td>{escape(g.get('direccion') or '')}</td>
          <td>N° de documentos</td>
          <td>{escape(g.get('documentos') or '')}</td>
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
          <td>Cajas / Bolsas / Cayvas / Sobres</td>
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
