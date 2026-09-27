#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers para renderizado de vistas HTML.
Layouts base, componentes reutilizables (chips, stepper, tablas).
"""
import html as _html

from guias_coodescor.config import (
    ESTADOS,
    PASO_POR_ESTADO,
    PASOS,
    ROL_LABEL,
)
from guias_coodescor.services.auth_service import obtener_config

_esc = _html.escape


def escape(val):
    if val is None:
        return ""
    return _esc(str(val))


def page(titulo: str, cuerpo: str, user: dict | None = None, extra: str = "") -> str:
    """Layout base: navegación + cuerpo + imports estáticos."""
    nav = ""
    if user:
        btn_nueva = (
            '<a class="btnnav" href="/guia/nueva">＋ Nueva guía</a>'
            if user.get("rol") == "ventas"
            else ""
        )
        btn_admin = (
            '<a href="/admin">Admin</a>'
            if user.get("rol") == "admin"
            else ""
        )
        empresa = escape(obtener_config("empresa", "Coodescor"))
        nav = f"""<nav><div class="navin">
        <span class="logo">📦 {empresa} <small>Guías</small></span>
        <a href="/tablero">Tablero</a><a href="/guias">Guías</a>
        {btn_nueva}
        {btn_admin}
        <button type="button" id="btn-toggle-tema" class="icon-btn" aria-label="Cambiar tema claro/oscuro" title="Cambiar tema (claro/oscuro/auto)">🌓</button>
        <span class="userchip">{escape(user.get('nombre'))} · {escape(ROL_LABEL.get(user.get('rol'), user.get('rol','')))}</span>
        <a href="#" onclick="cerrarSesion(); return false;">Salir</a>
        </div></nav>"""
    else:
        # Vistas públicas (login, firma token) también tienen toggle tema
        nav = f"""<nav><div class="navin">
        <span class="logo">📦 Guías Coodescor</span>
        <button type="button" id="btn-toggle-tema" class="icon-btn" aria-label="Cambiar tema claro/oscuro" title="Cambiar tema (claro/oscuro/auto)">🌓</button>
        </div></nav>"""
    
    # Meta tags para PWA
    meta_pwa = """
    <meta name="theme-color" content="#1d4ed8" id="meta-theme-color">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Guías Coodescor">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">
    <link rel="icon" type="image/svg+xml" href="/static/icons/icon.svg">
    """
    # Script NO-FOUC: aplica tema ANTES de pintar el CSS (sin parpadeo light->dark)
    script_tema_nofouc = r"""<script>
    (function(){
      try{
        var pref = localStorage.getItem('theme_preference') || 'auto';
        var dark = false;
        if (pref === 'dark') dark = true;
        else if (pref === 'light') dark = false;
        else dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
      }catch(e){ document.documentElement.setAttribute('data-theme','light'); }
    })();
    </script>"""
    
    # Service Worker registration script
    sw_script = """
    <script>
    // Registrar Service Worker para PWA
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/service-worker.js')
          .then(function(registration) {
            console.log('ServiceWorker registration successful');
          })
          .catch(function(err) {
            console.log('ServiceWorker registration failed: ', err);
          });
      });
    }
    
    // Detectar modo offline
    window.addEventListener('offline', function() {
      document.querySelector('.offline-banner').classList.add('show');
    });
    window.addEventListener('online', function() {
      document.querySelector('.offline-banner').classList.remove('show');
    });
    
    // Mostrar banner de instalación PWA
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      setTimeout(() => {
        const banner = document.querySelector('.pwa-install-banner');
        if (banner) {
          banner.classList.add('show');
        }
      }, 3000);
    });
    
    function installPWA() {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the install prompt');
          }
          deferredPrompt = null;
          document.querySelector('.pwa-install-banner').classList.remove('show');
        });
      }
    }
    </script>
    """
    
    # Banner de instalación PWA (se añade al body)
    pwa_banner = """
    <div class="pwa-install-banner" id="pwa-banner">
      <span>📱 <b>Instalar App</b> para acceso rápido desde tu dispositivo</span>
      <button onclick="installPWA();document.getElementById('pwa-banner').classList.remove('show')">Instalar</button>
      <button class="close-btn" onclick="document.getElementById('pwa-banner').classList.remove('show')">×</button>
    </div>
    <div class="offline-banner">⚠️ Modo offline - Algunos datos pueden no estar actualizados</div>
    """
    
    skip_link = r'<a href="#contenido" class="skip-link" aria-label="Saltar al contenido principal">Saltar al contenido</a>'
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
{meta_pwa}
<title>{escape(titulo)} · Guías Coodescor</title>
{script_tema_nofouc}
<link rel="stylesheet" href="/static/style.css"></head>
<body>{skip_link}{nav}<main id="contenido" tabindex="-1">{cuerpo}</main>
{pwa_banner}
<script src="/static/app.js"></script>{sw_script}{extra}</body></html>"""


def estado_chip(guia: dict) -> str:
    txt, color = ESTADOS.get(guia.get("estado", ""), (guia.get("estado", ""), "#666"))
    return f'<span class="chip" style="background:{escape(color)}">{escape(txt)}</span>'


def stepper(guia: dict) -> str:
    paso = PASO_POR_ESTADO.get(guia.get("estado", ""), 0)
    if guia.get("estado") == "ANULADA":
        return '<div class="stepper"><div class="paso mal">Guía anulada</div></div>'
    out = ['<div class="stepper">']
    for i, p in enumerate(PASOS):
        cls = "ok" if i < paso else ("act" if i == paso else "")
        out.append(f'<div class="paso {cls}"><b>{i+1}</b> {escape(p)}</div>')
    out.append("</div>")
    return "".join(out)


def img_adj(ruta: str | None, alt: str = "firma", cls: str = "firma") -> str:
    if not ruta:
        return '<span class="sin">—</span>'
    return f'<img class="{escape(cls)}" src="/static_file/{escape(ruta)}" alt="{escape(alt)}" loading="lazy">'


def fila(campo: str, valor) -> str:
    v = valor if valor not in (None, "") else None
    return (
        '<div class="kv"><span>'
        + escape(campo)
        + '</span><b>'
        + (escape(str(v)) if v is not None else "—")
        + '</b></div>'
    )


def fila_raw(campo: str, valor_html: str | None) -> str:
    """Igual que fila() pero NO escapa el valor: úsalo solo cuando valor_html
    ya es HTML seguro y preformateado (ej: chips span data-docs-chips ya escapado
    previamente, imágenes, etc.). Nunca pases aquí user input crudo."""
    return (
        '<div class="kv"><span>'
        + escape(campo)
        + '</span><b>'
        + (str(valor_html) if valor_html not in (None, "") else "—")
        + '</b></div>'
    )


def card_accion(tit: str, txt: str, href: str) -> str:
    return (
        f'<a class="cardaccion" href="{escape(href)}"><b>{escape(tit)}</b>'
        f'<span>{escape(txt)}</span></a>'
    )


def wrapper_acordeon(
    titulo: str,
    cuerpo_html: str,
    *,
    subtitulo: str | None = None,
    badge_texto: str | None = None,
    badge_tipo: str = "default",
    icono_texto: str = "▸",
    abierto_por_defecto: bool = False,
    id_acc: str | None = None,
) -> str:
    """Envuelve contenido HTML en un acordeón ERP colapsable.
       · Todas las secciones COMIENZAN CERRADAS por defecto (SPEC T6).
       · Usa abierto_por_defecto=True solo para secciones críticas prioritarias.
       · badge_tipo ∈ {default, aviso, ok, primary, danger}
    """
    cls_badge = f" acc-badge {badge_tipo}" if badge_tipo != "default" else " acc-badge"
    badge_html = (
        f'<span class="{cls_badge.strip()}">{escape(str(badge_texto))}</span>'
        if badge_texto not in (None, "")
        else ""
    )
    sub_html = f"<small>{escape(str(subtitulo))}</small>" if subtitulo else ""
    data_abierto = ' data-abierto="1"' if abierto_por_defecto else ""
    id_attr = f' id="{escape(str(id_acc))}"' if id_acc else ""
    return f"""
<article class="acc"{id_attr}{data_abierto}>
  <div class="acc-header" role="button" tabindex="0" aria-expanded="{'true' if abierto_por_defecto else 'false'}">
    <span class="acc-icono" aria-hidden="true">{escape(str(icono_texto))}</span>
    <div class="acc-tit">
      <h3>{escape(str(titulo))}</h3>
      {sub_html}
    </div>
    {badge_html}
  </div>
  <div class="acc-body">{cuerpo_html}</div>
</article>"""


def lista_guias(
    rows: list[dict],
    titulo: str,
    *,
    en_acordeon: bool = True,
    rol_usuario: str | None = None,
) -> str:
    """Renderiza una lista de guías con badge de cantidad.
       Si rol_usuario está en PERMISO_IMPRIMIR_GUIA, agrega botón 🖨️ Imprimir
       en cada fila (consistente con restricción transportador NO imprime).
    """
    from guias_coodescor.config import PERMISO_IMPRIMIR_GUIA
    puede_imprimir = bool(rol_usuario) and (rol_usuario in PERMISO_IMPRIMIR_GUIA)

    if not rows:
        cuerpo = "<p class='sin'>Sin pendientes 🎉</p>"
    else:
        def _fila(r: dict) -> str:
            cols = []
            cols.append(f"<b>No. {r['consecutivo']}</b>")
            cols.append(f"<span>{escape(r.get('cliente') or '')}</span>")
            meta = f"<small>{escape(r.get('ciudad') or '')} · {escape(r.get('creada_en') or '')}</small>"
            if puede_imprimir:
                btn_print = (
                    f'<a class="btn mini" style="margin-top:0;padding:6px 10px;font-size:12px;min-height:auto" '
                    f'href="/guia/{r["id"]}/imprimir" target="_blank" rel="noopener" '
                    f'onclick="event.stopPropagation()">🖨️</a>'
                )
                return (
                    f"<a class='item' href='/guia/{r['id']}' style='grid-template-columns:auto 1fr auto auto'>"
                    + cols[0] + cols[1] + meta
                    + estado_chip(dict(r))
                    + btn_print
                    + "</a>"
                )
            return (
                f"<a class='item' href='/guia/{r['id']}'>"
                + cols[0] + cols[1] + meta
                + estado_chip(dict(r))
                + "</a>"
            )

        items = "".join(_fila(r) for r in rows)
        cuerpo = f"<div class='lista'>{items}</div>"
    n = len(rows) if rows else 0
    badge = f"{n} guía{'s' if n != 1 else ''}" if n > 0 else "vacía"
    badge_tipo = "ok" if n == 0 else ("aviso" if n >= 5 else "primary")
    if not en_acordeon:
        return f"<section class='card'><h3>{escape(titulo)}</h3>{cuerpo}</section>"
    return wrapper_acordeon(
        titulo,
        cuerpo,
        badge_texto=badge,
        badge_tipo=badge_tipo,
        abierto_por_defecto=False,
    )
