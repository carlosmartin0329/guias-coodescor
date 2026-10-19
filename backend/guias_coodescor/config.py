




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuración centralizada del sistema de Guías Coodescor.

Separación de responsabilidades:
    - config.py  → constantes de negocio, red, seguridad y límites.
    - core/paths.py → dónde viven los DATOS y cómo se resuelven.
    - core/settings.py → validación tipada de entorno (.env, env vars, config.json).

Los datos (base, adjuntos, logs, respaldos) están FUERA de la carpeta del código.
Ver core/paths.py para la cadena de resolución y la migración de instalaciones
que tenían la base dentro del programa.
"""
import os

from guias_coodescor.core.paths import (
    BASE_DIR_PKG,
    escribir_json_atomico,
    leer_json,
    preparar,
    ruta_config_externo,
    ruta_secretos,
)
from guias_coodescor.core.settings import settings

BASE_DIR = BASE_DIR_PKG

# --- Datos: fuera de la carpeta del código (ver core/paths.py) --------------
_preparado = preparar()
DATA_DIR = _preparado["data_dir"]
DATA_DIR_ORIGEN = _preparado["origen"]
CONFIG_FILE = _preparado["config_file"]
ADJUNTOS_DIR = os.path.join(DATA_DIR, "adjuntos")
BACKUP_DIR = os.path.join(DATA_DIR, "respaldos")
SECRETOS_FILE = ruta_secretos(DATA_DIR)

# Rutas de CÓDIGO: permanecen dentro del paquete.
STATIC_DIR = os.path.join(BASE_DIR, "static")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "database", "migrations")

DB_PATH = os.path.join(DATA_DIR, "guias.db")
RECEPTORES_DB_PATH = os.path.join(DATA_DIR, "receptores.db")

# Nombre del secreto maestro de cifrado. El valor vive en DATA_DIR/secretos.json,
# nunca dentro de la base de datos.
RECEPTORES_SECRET_KEY_NAME = "receptores_secret_key"
CAPTCHA_SECRET_KEY_NAME = "captcha_hmac_secret_key"

# --- Red --------------------------------------------------------------------
# Validado por core/settings.Settings
HOST = settings.host
PORT = settings.port

# Orígenes permitidos para CORS. Vacío = solo mismo origen (valor por defecto y
# recomendado). Separate el frontend en otro puerto/dominio exige listar aquí su
# origen y servir por HTTPS con la cookie en SameSite=None; Secure.
CORS_ORIGINS = tuple(
    o.strip().rstrip("/")
    for o in settings.cors_origins.split(",")
    if o.strip()
)

# Solo se acepta X-Forwarded-For si la conexión viene de estos proxies.
TRUSTED_PROXIES = frozenset(
    p.strip() for p in settings.trusted_proxies.split(",") if p.strip()
)

MAX_REQUEST_BODY = settings.max_request_body
MAX_ADJUNTO_SIZE = settings.max_adjunto_size

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}
ALLOWED_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
}

SESSION_DURATION_SECONDS = 8 * 60 * 60
SESSION_COOKIE_NAME = "sid"
# Atributos de la cookie de sesión, configurables porque cambian según cómo se
# despliegue: HTTP en red local -> SameSite=Lax sin Secure; HTTPS con frontend
# en otro origen -> SameSite=None y Secure=True.
SESSION_COOKIE_SAME_SITE = str(settings.cors_origins and "None" or "Lax")
SESSION_COOKIE_SECURE = settings.environment == "production"

PASSWORD_MIN_LENGTH = 6
PASSWORD_HASH_ITERATIONS = 120_000
SALT_BYTE_LENGTH = 8
SID_BYTE_LENGTH = 24

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300
# Límite por IP: frena el credential stuffing distribuido, que el bloqueo por
# usuario no cubre. Cuenta intentos fallidos en una ventana de tiempo.
LOGIN_IP_MAX_ATTEMPTS = 20
LOGIN_IP_WINDOW_SECONDS = 300

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
    "administrativo": "Administrativo",
    "cedis": "CEDIS",
    "admin": "Admin del sistema",
    "transportador": "Transportador propio",
}

ROLES_VALIDOS = {"ventas", "administrativo", "cedis", "admin", "transportador", "publico"}

PERMISO = {
    "recepcion_admin": "administrativo",
    "control_cedis": "cedis",
    "entrega_transporte": "cedis",
    "entrega_cliente": "cedis",
    "anular": "admin",
    "edicion_guia": "ventas",
}

PERMISO_ADICIONAL_ROL = {
    "recepcion_admin": ["admin"],
    "control_cedis": ["admin"],
    # Entrega_transporte: solo CEDIS (principal) y ADMIN (backup).
    # Administrativo NO entrega al transportador para NO saltar el paso CEDIS.
    # Administrativo solo REGISTRA/LLENA los datos del transportador externo para que CEDIS
    # los vea pre-rellenados al momento de la entrega real (flujo: Ventas → Admin → Cedis → Cliente).
    "entrega_transporte": ["admin"],
    # Entrega_cliente: la cierra CEDIS (normal/directo), ADMIN (backup), TRANSPORTADOR (operario propio
    # del sistema logueado con usuario) y PUBLICO (cliente final sin login mediante link /firma/<TOKEN>).
    "entrega_cliente": ["transportador", "admin", "publico"],
    "anular": [],
    # Edicion_guia: permitidos todos los roles operativos, pero con restricción de estado
    # por rol en services/guias_service.py validar_transicion ("__EDITABLE__" por rol).
    "edicion_guia": ["admin", "administrativo", "ventas", "cedis"],
}

# Permisos adicionales (fuera de eventos de guía) usados en servicios/vistas:
PERMISO_EXPORTAR_AUDITORIA = {"admin", "administrativo"}
PERMISO_IMPRIMIR_GUIA = {"admin", "ventas", "administrativo", "cedis"}
PERMISO_ASIGNAR_TIPO_TRANSPORTADOR = {"admin", "administrativo"}
PERMISO_REGISTRAR_TRANSPORTADOR_EXTERNO = {"admin", "administrativo"}

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
    # Entrega_transporte SÓLO cuando la guía está EN_CEDIS (después de control_cedis de CEDIS).
    # Garantiza el flujo Ventas → Admin → Transportador (registro) → Cedis (control + entrega) → Cliente.
    "entrega_transporte": "EN_CEDIS",
    "entrega_cliente": "__EN_RUTA_O_EN_CEDIS__",
    "anular": None,
    "edicion_guia": "__EDITABLE__",
}

TIPO_TITULO = {
    "creacion": "Creación y entrega de ventas",
    "recepcion_admin": "Recepción y Asignación Administrativa",
    "envio_directo_cedis": "Envío directo a CEDIS (sin paso por admin)",
    "control_cedis": "Control CEDIS / vechículo",
    "entrega_transporte": "Entrega al transportador",
    "entrega_cliente": "Entrega al cliente / farmacia",
    "anular": "Anulación",
    "edicion_guia": "Edición de datos de la guía (auditoría)",
}

DEFAULT_USERS = [
    ("admin", "Administrador del sistema", "admin123", "admin"),
    ("administrativo", "Usuario Administrativo", "adminbod123", "administrativo"),
    ("ventas", "Usuario Ventas 1", "ventas123", "ventas"),
    ("ventas2", "Usuario Ventas 2", "ventas123", "ventas"),
    ("ventas3", "Usuario Ventas 3", "ventas123", "ventas"),
    ("ventas4", "Usuario Ventas 4", "ventas123", "ventas"),
    ("ventas5", "Usuario Ventas 5 (loadtest)", "ventas123", "ventas"),
    ("cedis", "Usuario CEDIS", "cedis123", "cedis"),
    ("cedis2", "Usuario CEDIS 2 (loadtest)", "cedis123", "cedis"),
    # --- Transportadores propios (operarios con login): rol = transportador ---
    ("transportador", "Transportador Propio 1", "transpor123", "transportador"),
    ("transportador2", "Transportador Propio 2", "transpor123", "transportador"),
    ("transportador3", "Transportador Propio 3", "transpor123", "transportador"),
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

# --- Respaldos automáticos de la base de datos -----------------------------
# Un respaldo íntegro y consistente antes de cualquier operación destructiva
# es la garantía mínima para poder editar datos desde la aplicación.
BACKUP_RETENTION = 30
# Tamaño máximo permitido a un archivo de base de datos al restaurar (protege
# contra subir un archivo arbitrario enorme).
MAX_DB_BACKUP_SIZE = 2 * 1024 * 1024 * 1024

# --- Módulo de administración de la base de datos --------------------------
# Tablas que solo se pueden leer: son internas del motor y no admiten edición
# manual (alterarlas rompe la auditoría o el control de versiones del esquema).
DB_TABLAS_SOLO_LECTURA = frozenset({"sqlite_sequence", "schema_migrations", "sesiones"})
# Tablas cuyo contenido es cifrado: se muestran enmascaradas y no se editan
# desde la interfaz para no exponer datos personales ni romper el cifrado.
DB_TABLAS_CIFRADAS = frozenset({"receptores"})
# Tope de filas devueltas por página en el explorador, para no agotar la memoria.
DB_PAGE_SIZE_MAX = 200
DB_QUERY_TIMEOUT_MS = 5000
DB_QUERY_MAX_ROWS = 500

# ============================================================================
# Configuración del Servicio de IA (Opcional)
# ============================================================================
# API Keys para proveedores de IA gratuitos.
# Puedes configurarlos aquí o mediante variables de entorno:
#   - HUGGINGFACE_API_KEY
#   - MISTRAL_API_KEY
#   - GROQ_API_KEY
#   - GOOGLE_GEMINI_API_KEY
#
# Proveedores gratuitos disponibles:
#   - Hugging Face: Sin API Key necesaria (pero recomendada para más solicitudes)
#   - Mistral AI: API Key gratuita en https://console.mistral.ai/
#   - Groq: API Key gratuita en https://console.groq.com/
#   - Google Gemini: API Key gratuita en https://aistudio.google.com/
AI_HUGGINGFACE_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")
AI_MISTRAL_KEY = os.environ.get("MISTRAL_API_KEY", "")
AI_GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
AI_GOOGLE_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")

# Configuración de modelos por defecto
AI_DEFAULT_PROVIDER = "huggingface"  # Proveedor por defecto
AI_DEFAULT_MODEL = {
    "huggingface": "mistralai/Mistral-7B-instruct",
    "mistral": "mistral-tiny",
    "groq": "llama3-8b-8192",
    "google": "gemini-1.5-flash",
}

# Timeout para solicitudes de IA (segundos)
AI_REQUEST_TIMEOUT = 30
