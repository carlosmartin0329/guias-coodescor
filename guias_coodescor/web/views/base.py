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
        <span class="userchip">{escape(user.get('nombre'))} · {escape(ROL_LABEL.get(user.get('rol'), user.get('rol','')))}</span>
        <a href="#" onclick="postJSON('/api/logout',{{}});return false;">Salir</a>
        </div></nav>"""
    
    # Meta tags para PWA
    meta_pwa = """
    <meta name="theme-color" content="#1d4ed8">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Guías Coodescor">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">
    <link rel="icon" type="image/svg+xml" href="/static/icons/icon.svg">
    """
    
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
    
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
{meta_pwa}
<title>{escape(titulo)} · Guías Coodescor</title>
<link rel="stylesheet" href="/static/style.css"></head>
<body>{nav}<main>{cuerpo}</main>
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


def card_accion(tit: str, txt: str, href: str) -> str:
    return (
        f'<a class="cardaccion" href="{escape(href)}"><b>{escape(tit)}</b>'
        f'<span>{escape(txt)}</span></a>'
    )


def lista_guias(rows: list[dict], titulo: str) -> str:
    if not rows:
        return f"<section class='card'><h3>{escape(titulo)}</h3><p class='sin'>Sin pendientes 🎉</p></section>"
    items = "".join(
        f"<a class='item' href='/guia/{r['id']}'><b>No. {r['consecutivo']}</b>"
        f"<span>{escape(r.get('cliente') or '')}</span>"
        f"<small>{escape(r.get('ciudad') or '')} · {escape(r.get('creada_en') or '')}</small>"
        f"{estado_chip(dict(r))}</a>" for r in rows
    )
    return f"<section class='card'><h3>{escape(titulo)}</h3><div class='lista'>{items}</div></section>"
