#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servicio CAPTCHA 100% stdlib.

- Genera desafíos alfanuméricos de 6 caracteres (sin ambigüedades 0/O/1/I).
- Renderiza SVG inline distorsionado (rotaciones, translaciones, trazos ruido).
- Emite token HMAC-SHA256 firmado con un secreto persistido en
  DATA_DIR/secretos.json (captcha_hmac_secret_key), fuera de la base de datos —
  NO viaja la respuesta en texto plano.
- Nonce de un solo uso con TTL 360 s.
- Expiración 300 s por desafío.
- Bypass seguro para tests automatizados: vía variable entorno + header HTTP
  (nunca habilitado por defecto en producción).
"""
import base64
import hashlib
import hmac
import html
import logging
import os
import random
import secrets
import threading
import time
import uuid
from typing import Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LONGITUD_DESAFIO = 6
SEGUNDOS_EXPIRACION = 300
SEGUNDOS_TTL_NONCE = 360
CONFIG_KEY_CAPTCHA_SECRET = "captcha_hmac_secret_key"
ENV_BYPASS_KEY = "COODESCOR_CAPTCHA_BYPASS_KEY"

_NONCES_LOCK = threading.Lock()
_NONCES_USED: Dict[str, float] = {}
_SECRET_LOCK = threading.Lock()
_MEMOIZED_SECRET: str = ""


def _purgar_lazy_nonces(ahora: float) -> None:
    with _NONCES_LOCK:
        if len(_NONCES_USED) < 2000 and int(ahora) % 17 != 0:
            return
        limpiar = [k for k, v in _NONCES_USED.items() if (ahora - v) > SEGUNDOS_TTL_NONCE]
        for k in limpiar:
            _NONCES_USED.pop(k, None)


def _captcha_secret() -> str:
    global _MEMOIZED_SECRET
    if _MEMOIZED_SECRET:
        return _MEMOIZED_SECRET
    with _SECRET_LOCK:
        if _MEMOIZED_SECRET:
            return _MEMOIZED_SECRET
        from guias_coodescor.config import DATA_DIR
        from guias_coodescor.core.paths import asegurar_secreto

        _MEMOIZED_SECRET = asegurar_secreto(
            DATA_DIR, CONFIG_KEY_CAPTCHA_SECRET, lambda: secrets.token_urlsafe(48)
        )
        return _MEMOIZED_SECRET


def _normalizar_respuesta(resp: str) -> str:
    return "".join(c for c in (resp or "").strip().upper() if c in ALFABETO or c in "01IO")


def _desafio_random() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD_DESAFIO))


def _render_svg(desafio: str, width: int = 260, height: int = 80) -> str:
    rnd = random.Random(secrets.randbits(64))
    palette_line = [
        "#3b82f6", "#1d4ed8", "#0ea5e9", "#2563eb", "#6366f1",
        "#0891b2", "#475569", "#64748b",
    ]
    char_w = width / len(desafio)
    chars_svg: List[str] = []
    for i, ch in enumerate(desafio):
        x = 14 + i * char_w
        y_base = 56 + rnd.uniform(-5, 7)
        rotate = rnd.uniform(-22, 22)
        dy = rnd.uniform(-4, 4)
        color = rnd.choice(palette_line[:6])
        weight = rnd.choice([600, 700, 800, 900])
        size = rnd.randint(34, 44)
        chars_svg.append(
            f'<text x="{x:.1f}" y="{y_base:.1f}" '
            f'fill="{color}" font-size="{size}" font-weight="{weight}" '
            f'font-family="Consolas, ui-monospace, monospace" '
            f'transform="rotate({rotate:.1f} {x:.1f} {y_base:.1f}) translate(0 {dy:.1f})" '
            f'style="user-select:none;-webkit-user-select:none">{html.escape(ch)}</text>'
        )
    lines_noise: List[str] = []
    for _ in range(7):
        x1 = rnd.randint(0, width)
        y1 = rnd.randint(6, height - 6)
        x2 = rnd.randint(0, width)
        y2 = rnd.randint(6, height - 6)
        color = rnd.choice(palette_line)
        sw = rnd.choice([1.0, 1.3, 1.6, 2.0])
        lines_noise.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" opacity="0.45"/>'
        )
    dots: List[str] = []
    for _ in range(40):
        cx = rnd.randint(1, width - 1)
        cy = rnd.randint(1, height - 1)
        r = rnd.uniform(0.8, 2.2)
        color = rnd.choice(palette_line)
        dots.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{color}" opacity="0.35"/>'
        )
    grad = (
        '<defs><linearGradient id="cg" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0" stop-color="var(--surface)"/>'
        '<stop offset="1" stop-color="var(--surface-elevada)"/>'
        "</linearGradient></defs>"
    )
    border_color = "var(--borde)"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'class="captcha-image" role="img" aria-label="Imagen CAPTCHA con 6 letras, código visual de seguridad. '
        f'Escribe los 6 caracteres en el campo de respuesta." preserveAspectRatio="xMidYMid meet">'
        f"{grad}"
        f'<rect x="1" y="1" rx="10" ry="10" width="{width-2}" height="{height-2}" '
        f'fill="url(#cg)" stroke="{border_color}" stroke-width="1.5"/>'
        + "".join(lines_noise)
        + "".join(dots)
        + "".join(chars_svg)
        + "</svg>"
    )
    return svg


def _canonical_ip(ip: str) -> str:
    s = (ip or "").strip()
    if s.startswith("::ffff:"):
        s = s[7:]
    if s == "::1":
        s = "127.0.0.1"
    return s


def generar_captcha(ip: str = "", ua: str = "") -> Tuple[str, str, str]:
    """
    Devuelve (desafio_real, svg_html, token_firmado).
    - El CALLER NO debe enviar `desafio_real` al cliente.
    - Solo se envía `svg_html` y `token_firmado`.
    - Token codifica: v1 | exp_ts | nonce | hmac_sha256(ip|ua|desafio|exp|nonce, secret)
    """
    ip_orig = (ip or "").strip()
    ip_n = _canonical_ip(ip_orig)[:64]
    ua_n = (ua or "").strip()[:160]
    desafio = _desafio_random()
    ahora = time.time()
    exp = int(ahora + SEGUNDOS_EXPIRACION)
    nonce = uuid.uuid4().hex
    payload_sin_firma = f"v1|{exp}|{nonce}|{desafio}"
    msg = f"{ip_n}\n{ua_n}\n{payload_sin_firma}"
    mac = hmac.new(_captcha_secret().encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    token_b64 = base64.urlsafe_b64encode(
        f"{payload_sin_firma}|{mac}".encode("utf-8")
    ).decode("ascii").rstrip("=")
    svg = _render_svg(desafio)
    logger.info(
        "CAPTCHA generar: ip_orig=%r ip_can=%r ua_len=%d nonce=%s exp=%d",
        ip_orig, ip_n, len(ua_n), nonce[:8], exp,
    )
    return desafio, svg, token_b64


def _check_bypass_header(header_value: str) -> bool:
    esperado = os.environ.get(ENV_BYPASS_KEY, "")
    if not esperado:
        return False
    return hmac.compare_digest(esperado, header_value or "")


def validar_captcha(
    token: str,
    respuesta: str,
    ip: str = "",
    ua: str = "",
    bypass_header: str = "",
) -> Tuple[bool, str]:
    """
    Valida respuesta CAPTCHA.
    - bypass_header NO hace bypass a menos que la variable entorno exista y coincida
      en comparación constante-tiempo.
    Devuelve (valido: bool, mensaje: str).
    """
    ahora = time.time()
    _purgar_lazy_nonces(ahora)

    if bypass_header and _check_bypass_header(bypass_header):
        return True, "ok-bypass"

    if not token:
        return False, "CAPTCHA faltante. Actualiza la página e intenta de nuevo."
    if not respuesta:
        return False, "Ingresa el código CAPTCHA mostrado en la imagen."
    try:
        padding = "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(token + padding).decode("utf-8")
        trozos = decoded.split("|")
        if len(trozos) != 5 or trozos[0] != "v1":
            return False, "CAPTCHA corrupto. Actualiza la página e intenta de nuevo."
        _, exp_str, nonce, desafio, mac_cliente = trozos
        exp = int(exp_str)
    except Exception:
        return False, "CAPTCHA corrupto. Actualiza la página e intenta de nuevo."

    if exp < int(ahora):
        return False, "CAPTCHA expiró. Recarga el código CAPTCHA e intenta de nuevo."

    with _NONCES_LOCK:
        if nonce in _NONCES_USED:
            return False, "CAPTCHA ya usado. Genera uno nuevo e intenta de nuevo."
        _NONCES_USED[nonce] = ahora

    ip_orig = (ip or "").strip()
    ip_n = _canonical_ip(ip_orig)[:64]
    ua_n = (ua or "").strip()[:160]
    payload_sin_firma = f"v1|{exp}|{nonce}|{desafio}"
    msg = f"{ip_n}\n{ua_n}\n{payload_sin_firma}"
    mac_esperado = hmac.new(
        _captcha_secret().encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    hmac_ok = hmac.compare_digest(mac_esperado, mac_cliente)
    if not hmac_ok:
        logger.warning(
            "CAPTCHA hmac NO COINCIDE: ip_orig=%r ip_can=%r ua_len=%d nonce=%s ip_al_token=%s mismatched_ips=%s",
            ip_orig, ip_n, len(ua_n), nonce[:8],
            "OK_SAME" if (ip_orig and _canonical_ip(ip_orig) == ip_n) else "DIFF",
            "NO" if ip_orig else "SI_IP_VACIO",
        )
        return False, "CAPTCHA inválido o alterado. Intenta de nuevo."

    rta_norm = (respuesta or "").strip().upper()
    tabla_tr = str.maketrans({"0": "O", "1": "I"})
    rta_canon = rta_norm.translate(tabla_tr)
    if not hmac.compare_digest(desafio, rta_canon) and desafio != rta_norm:
        logger.info(
            "CAPTCHA respuesta INCORRECTA: nonce=%s user_rta=%r esperado_canon=%r (esperado_raw=%r)",
            nonce[:8], rta_norm[:16], desafio, desafio,
        )
        return False, "Código CAPTCHA incorrecto. Revisa mayúsculas y números."

    logger.info("CAPTCHA OK: nonce=%s ip_can=%r ua_len=%d", nonce[:8], ip_n, len(ua_n))
    return True, "ok"
