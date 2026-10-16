#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cifrado simétrico ligero 100% Python stdlib.
Algoritmo: PBKDF2-HMAC-SHA256 (120k iter) + salt aleatorio por registro +
XOR stream cipher + HMAC-SHA256 integridad (tamper-detection).

Formato columna cifrada (5 partes separadas por $):
  $1$PBKDF2$<salt_b64>$<ciphertext_b64>$<hmac_tag_b64>

Propósito: cifrar PII en tabla receptores SIN depender de paquetes externos
(cumple regla invariable stdlib-only para compatibilidad Android APK).

No es AES-GCM (no existe en stdlib). El nivel de seguridad adecuado para:
  - Datos operativos internos (receptores guías),
  - Clave maestra de 256-bit guardada en config.tabla (nunca hardcodeada),
  - Salt 16-byte por registro (2 registros iguales plaintext → ciphertexts DIFERENTES).
"""
import base64
import hashlib
import hmac
import secrets

_CIF_VERSION = "$1$PBKDF2$"
_PBKDF2_ITER = 120_000
_KEY_LEN = 32
_SALT_LEN = 16
_HMAC_LEN = 32
_SEP = "$"


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def cifrar_valor(plain: str, master_secret: str) -> str:
    """Cifra un string y retorna el formato con metadatos incorporados.
    Si plain es None o "" retorna "" (no ciframos vacíos).
    """
    if plain is None:
        return ""
    plain = str(plain)
    if plain == "":
        return ""
    plain_bytes = plain.encode("utf-8")
    salt = secrets.token_bytes(_SALT_LEN)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        master_secret.encode("utf-8"),
        salt,
        _PBKDF2_ITER,
        dklen=_KEY_LEN,
    )
    repeats = (len(plain_bytes) // _KEY_LEN) + 1
    keystream = (derived * repeats)[: len(plain_bytes)]
    cipher = bytes(a ^ b for a, b in zip(plain_bytes, keystream))
    tag = hmac.new(derived, cipher + salt, hashlib.sha256).digest()
    return (
        _CIF_VERSION
        + _b64e(salt)
        + _SEP
        + _b64e(cipher)
        + _SEP
        + _b64e(tag)
    )


def descifrar_valor(cifrado: str, master_secret: str) -> str | None:
    """Descifra un string producido por cifrar_valor.
    Retorna None si: el formato es inválido, la clave es incorrecta o hubo
    corrupción de datos (fallo HMAC). NEVER lanza excepciones.
    """
    if not cifrado:
        return ""
    if not isinstance(cifrado, str):
        return None
    if not cifrado.startswith(_CIF_VERSION):
        return None
    try:
        payload = cifrado[len(_CIF_VERSION) :]
        parts = payload.split(_SEP)
        if len(parts) != 3:
            return None
        salt_b64, cipher_b64, tag_b64 = parts
        salt = _b64d(salt_b64)
        cipher = _b64d(cipher_b64)
        tag = _b64d(tag_b64)
        if len(salt) != _SALT_LEN or len(tag) != _HMAC_LEN:
            return None
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            master_secret.encode("utf-8"),
            salt,
            _PBKDF2_ITER,
            dklen=_KEY_LEN,
        )
        expected_tag = hmac.new(derived, cipher + salt, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_tag, tag):
            return None
        repeats = (len(cipher) // _KEY_LEN) + 1
        keystream = (derived * repeats)[: len(cipher)]
        plain_bytes = bytes(a ^ b for a, b in zip(cipher, keystream))
        return plain_bytes.decode("utf-8")
    except Exception:
        return None
