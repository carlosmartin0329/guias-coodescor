




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada del sistema de Guías Coodescor.
Todas las rutas, constantes y parámetros globales se definen aquí.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
ADJUNTOS_DIR = os.path.join(DATA_DIR, "adjuntos")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "database", "migrations")

DB_PATH = os.path.join(DATA_DIR, "guias.db")

HOST = "0.0.0.0"
PORT = 8000

MAX_REQUEST_BODY = 30 * 1024 * 1024
MAX_ADJUNTO_SIZE = 10 * 1024 * 1024

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}
ALLOWED_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
}

SESSION_DURATION_SECONDS = 8 * 60 * 60
SESSION_COOKIE_NAME = "sid"

PASSWORD_MIN_LENGTH = 6
PASSWORD_HASH_ITERATIONS = 120_000
SALT_BYTE_LENGTH = 8
SID_BYTE_LENGTH = 24

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300

ESTADOS = {
    "CREADA":         ("Creada · espera recepción / envío directo", "#b45309"),
    "RECIBIDA_ADMIN": ("En bodega · espera control CEDIS",            "#2563eb"),
    "EN_CEDIS":       ("Control CEDIS listo · espera transportador",  "#7c3aed"),
    "EN_RUTA":        ("En ruta · espera entrega al cliente",         "#0284c7"),
    "ENTREGADA":      ("Entregada",                                   "#15803d"),
    "ANULADA":        ("Anulada",                                     "#b91c1c"),
}

PASOS = ["Ventas", "Administración", "Control CEDIS", "Transportador", "Entrega cliente"]

PASO_POR_ESTADO = {"CREADA": 1, "RECIBIDA_ADMIN": 2, "EN_CEDIS": 3, "EN_RUTA": 4, "ENTREGADA": 5}

ROL_LABEL = {
    "ventas": "Ventas",
    "administrativo": "Administrativo (bodega)",
    "cedis": "CEDIS",
    "transportador": "Transportador",
    "admin": "Admin del sistema",
}

ROLES_VALIDOS = {"ventas", "administrativo", "cedis", "transportador", "admin"}

PERMISO = {
    "recepcion_admin": "administrativo",
    "control_cedis": "cedis",
    "entrega_transporte": "transportador",
    "entrega_cliente": "transportador",
    "anular": "admin",
    "edicion_guia": "ventas",
}

PERMISO_ADICIONAL_ROL = {
    "recepcion_admin": ["admin"],
    "control_cedis": [],
    "entrega_transporte": ["cedis"],
    "entrega_cliente": ["cedis"],
    "anular": [],
    "edicion_guia": ["admin"],
}

TRANSICION = {
    "recepcion_admin": "RECIBIDA_ADMIN",
    "envio_directo_cedis": "EN_CEDIS",
    "control_cedis": "EN_CEDIS",
    "entrega_transporte": "EN_RUTA",
    "entrega_cliente": "ENTREGADA",
    "anular": "ANULADA",
    "edicion_guia": None,
}

ESTADO_ESPERADO_POR_EVENTO = {
    "recepcion_admin": "CREADA",
    "envio_directo_cedis": "CREADA",
    "control_cedis": "__RECIBIDA_O_EN_CEDIS__",
    "entrega_transporte": "EN_CEDIS",
    "entrega_cliente": "__EN_RUTA_O_EN_CEDIS__",
    "anular": None,
    "edicion_guia": "__EDITABLE__",
}

TIPO_TITULO = {
    "creacion": "Creación y entrega de ventas",
    "recepcion_admin": "Recepción Administrativa (bodega)",
    "envio_directo_cedis": "Envío directo a CEDIS (sin paso por admin)",
    "control_cedis": "Control CEDIS / vechículo",
    "entrega_transporte": "Entrega al transportador",
    "entrega_cliente": "Entrega al cliente / farmacia",
    "anular": "Anulación",
    "edicion_guia": "Edición de datos de la guía (auditoría)",
}

DEFAULT_USERS = [
    ("admin", "Administrador del sistema", "admin123", "admin"),
    ("administrativo", "Usuario Administrativo (bodega)", "adminbod123", "administrativo"),
    ("ventas", "Usuario Ventas 1", "ventas123", "ventas"),
    ("ventas2", "Usuario Ventas 2", "ventas123", "ventas"),
    ("ventas3", "Usuario Ventas 3", "ventas123", "ventas"),
    ("ventas4", "Usuario Ventas 4", "ventas123", "ventas"),
    ("cedis", "Usuario CEDIS", "cedis123", "cedis"),
    ("transportador", "Usuario Transportador", "trans123", "transportador"),
]

DEFAULT_CONFIG = [
    ("siguiente", "45692"),
    ("empresa", "Coodescor"),
    ("pie", "Nit. 901836934-0 · Cel.: 3005762831"),
    ("lista_clientes_json", "[]"),
    ("vinculo_db_externo", ""),
    ("vinculo_db_externo_tipo", "ninguno"),
    ("vinculo_db_externo_url", ""),
    ("vinculo_db_externo_token", ""),
]

LOG_DIR = DATA_DIR
LOG_FILE = os.path.join(LOG_DIR, "guias_coodescor.log")
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
LOG_LEVEL = "INFO"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ADJUNTOS_DIR, exist_ok=True)
os.makedirs(MIGRATIONS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
