#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Definición del esquema de base de datos y inicialización.
Incluye migraciones, índices de rendimiento y datos semilla (seed data).
"""
import os
import sqlite3

from guias_coodescor.config import (
    DEFAULT_CONFIG,
    DEFAULT_USERS,
    MIGRATIONS_DIR,
)
from guias_coodescor.database.connection import db_connection, get_connection
from guias_coodescor.core.utils import ahora_txt, hash_password_puro


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL COLLATE NOCASE,
    nombre TEXT NOT NULL,
    pass_hash TEXT NOT NULL,
    sal TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('ventas','administrativo','cedis','admin','transportador')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado TEXT NOT NULL,
    ultima_sesion TEXT,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta TEXT
);

CREATE TABLE IF NOT EXISTS sesiones (
    sid TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    creada TEXT NOT NULL,
    expira TEXT NOT NULL,
    ip TEXT,
    user_agent TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS guias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consecutivo INTEGER UNIQUE NOT NULL,
    cliente TEXT,
    nit TEXT,
    centro_operacion TEXT,
    prefijo TEXT CHECK (prefijo IS NULL OR prefijo IN ('FV','TB','PD','TR')),
    ciudad TEXT,
    direccion TEXT,
    documentos TEXT,
    obs_ventas TEXT,
    envio_directo_cedis INTEGER NOT NULL DEFAULT 0 CHECK (envio_directo_cedis IN (0,1)),
    creada_por INTEGER,
    creada_en TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'CREADA'
        CHECK (estado IN ('CREADA','RECIBIDA_ADMIN','EN_CEDIS','EN_RUTA','ENTREGADA','ANULADA')),
    anulada_motivo TEXT,
    anulada_por INTEGER,
    anulada_en TEXT,
    tipo_transportador TEXT CHECK (tipo_transportador IN (NULL,'propio','externo')),
    transportador_asignado_id INTEGER,
    FOREIGN KEY (creada_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (anulada_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (transportador_asignado_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (nit) REFERENCES clientes(nit) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS clientes (
    nit TEXT PRIMARY KEY NOT NULL COLLATE NOCASE,
    razon_social TEXT NOT NULL,
    direccion TEXT,
    ciudad TEXT,
    telefono TEXT,
    email TEXT,
    contacto TEXT,
    forma_pago_default TEXT,
    observaciones TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    cliente_descubierto INTEGER NOT NULL DEFAULT 0 CHECK (cliente_descubierto IN (0,1)),
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guia_id INTEGER NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('creacion','recepcion_admin','envio_directo_cedis','control_cedis','entrega_transporte','entrega_cliente','anular','edicion_guia','receptor_purgado','captura_reclamo')),
    usuario_id INTEGER,
    usuario TEXT,
    rol TEXT,
    en TEXT NOT NULL,
    dispositivo TEXT,
    ip TEXT,
    datos TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (guia_id) REFERENCES guias(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS entrega_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guia_id INTEGER NOT NULL UNIQUE,
    token TEXT UNIQUE NOT NULL,
    creado_por INTEGER,
    creado_rol TEXT,
    creado_en TEXT NOT NULL,
    expira TEXT NOT NULL,
    usado_en TEXT,
    usado_ip TEXT,
    usado_ua TEXT,
    FOREIGN KEY (guia_id) REFERENCES guias(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    aplicada_en TEXT NOT NULL
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_guias_estado ON guias(estado);
CREATE INDEX IF NOT EXISTS idx_guias_creada_en ON guias(creada_en);
CREATE INDEX IF NOT EXISTS idx_guias_cliente ON guias(cliente);
CREATE INDEX IF NOT EXISTS idx_guias_consecutivo ON guias(consecutivo);
CREATE INDEX IF NOT EXISTS idx_guias_nit ON guias(nit);
CREATE INDEX IF NOT EXISTS idx_clientes_razon_social ON clientes(razon_social);
CREATE INDEX IF NOT EXISTS idx_clientes_ciudad ON clientes(ciudad);
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono);
CREATE INDEX IF NOT EXISTS idx_eventos_guia_id ON eventos(guia_id);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON eventos(tipo);
CREATE INDEX IF NOT EXISTS idx_eventos_en ON eventos(en);
CREATE INDEX IF NOT EXISTS idx_sesiones_usuario_id ON sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_sesiones_expira ON sesiones(expira);
CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario);
"""

RECEPTORES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS receptores (
    id_temp INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    nit_cliente TEXT NOT NULL,
    nombres_apellidos_cif TEXT NOT NULL,
    tipo_doc TEXT NOT NULL,
    numero_doc_cif TEXT NOT NULL,
    telefono_cif TEXT,
    email_cif TEXT,
    relacion_con_cliente TEXT,
    registrado_por TEXT NOT NULL,
    registrado_en TEXT NOT NULL,
    vence_en TEXT NOT NULL,
    guia_relacionada_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_receptores_nit_cliente ON receptores(nit_cliente);
CREATE INDEX IF NOT EXISTS idx_receptores_guia_id ON receptores(guia_relacionada_id);
CREATE INDEX IF NOT EXISTS idx_receptores_vence ON receptores(vence_en);
"""


def _asegurar_columna(conn, tabla: str, columna: str, definicion: str):
    columnas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    nombres = {fila[1] for fila in columnas}
    if columna not in nombres:
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {definicion}")


def _asegurar_columnas(conn):
    """Completa columnas que agregaron versiones antiguas y migraciones.

    Se ejecuta antes y después de las migraciones: en BDs antiguas faltan
    columnas que el CREATE TABLE IF NOT EXISTS no añade (por ejemplo
    clientes.metadata / cliente_descubierto, usadas por clientes_service).
    """
    _asegurar_columna(conn, "usuarios", "ultima_sesion", "ultima_sesion TEXT")
    _asegurar_columna(conn, "usuarios", "intentos_fallidos", "intentos_fallidos INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "usuarios", "bloqueado_hasta", "bloqueado_hasta TEXT")

    _asegurar_columna(conn, "sesiones", "expira", "expira TEXT NOT NULL DEFAULT ''")
    _asegurar_columna(conn, "sesiones", "ip", "ip TEXT")
    _asegurar_columna(conn, "sesiones", "user_agent", "user_agent TEXT")

    _asegurar_columna(conn, "guias", "envio_directo_cedis", "envio_directo_cedis INTEGER NOT NULL DEFAULT 0 CHECK (envio_directo_cedis IN (0,1))")
    _asegurar_columna(conn, "guias", "anulada_por", "anulada_por INTEGER")
    _asegurar_columna(conn, "guias", "anulada_en", "anulada_en TEXT")
    _asegurar_columna(conn, "guias", "nit", "nit TEXT")
    _asegurar_columna(conn, "guias", "centro_operacion", "centro_operacion TEXT")
    _asegurar_columna(conn, "guias", "prefijo", "prefijo TEXT")
    _asegurar_columna(conn, "guias", "tipo_transportador", "tipo_transportador TEXT")
    _asegurar_columna(conn, "guias", "transportador_asignado_id", "transportador_asignado_id INTEGER")

    _asegurar_columna(conn, "eventos", "ip", "ip TEXT")

    # Columnas del sprint de autocompletado de clientes: solo estaban en el
    # CREATE TABLE nuevo, ninguna migración las agregaba a instalaciones viejas.
    _asegurar_columna(conn, "clientes", "metadata", "metadata TEXT NOT NULL DEFAULT '{}'")
    _asegurar_columna(conn, "clientes", "cliente_descubierto", "cliente_descubierto INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "clientes", "contacto", "contacto TEXT")
    _asegurar_columna(conn, "clientes", "forma_pago_default", "forma_pago_default TEXT")
    _asegurar_columna(conn, "clientes", "observaciones", "observaciones TEXT")


def _crear_tablas(conn):
    conn.executescript(SCHEMA_SQL)
    _asegurar_columnas(conn)
    conn.executescript(INDEXES_SQL)


def _seed_usuarios(conn, ahora: str):
    """
    Crea los usuarios iniciales SOLO si no existen.

    Importante: nunca se reescribe un usuario existente. Las versiones
    anteriores actualizaban pass_hash, sal, rol y activo en cada arranque, lo
    que hacía inútil cambiar una contraseña desde el panel (al reiniciar volvía
    a la clave del seed) y reactivaba cuentas desactivadas a propósito.

    - Usuario inexistente  → INSERT con la clave inicial.
    - Usuario existente    → no se toca (respetar lo que configuró el admin).
    - Usuario NO listado en DEFAULT_USERS → jamás se crea ni se modifica.
    """
    for usuario, nombre, clave, rol in DEFAULT_USERS:
        existe = conn.execute(
            "SELECT 1 FROM usuarios WHERE usuario = ? COLLATE NOCASE",
            (usuario,),
        ).fetchone()
        if existe:
            continue
        pass_hash, sal = hash_password_puro(clave)
        conn.execute(
            """
            INSERT INTO usuarios(usuario, nombre, pass_hash, sal, rol, creado, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (usuario, nombre, pass_hash, sal, rol, ahora),
        )


def _seed_config(conn):
    for clave, valor in DEFAULT_CONFIG:
        conn.execute(
            "INSERT OR IGNORE INTO config(clave, valor) VALUES (?, ?)",
            (clave, valor),
        )


def _registrar_migracion_inicial(conn, ahora: str):
    fila = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = 1"
    ).fetchone()
    if not fila:
        conn.execute(
            "INSERT INTO schema_migrations(version, nombre, aplicada_en) VALUES (?, ?, ?)",
            (1, "migracion_inicial", ahora),
        )


def init_db():
    """
    Inicializa la base de datos:
    1. Crea tablas e índices si no existen.
    2. Aplica migraciones pendientes (ANTES de sembrar usuarios).
    3. Vuelve a asegurar columnas/índices que una migración pudo dejar
       incompletos.
    4. Inserta datos semilla (usuarios y config) solo si no existen.
    5. Traslada los secretos de la tabla config a DATA_DIR/secretos.json.
    6. Limpia sesiones expiradas.
    7. Crea el archivo receptores.db y sus tablas.

    El orden importa: antes se sembraban los usuarios primero y, en una BD
    anterior a V6, el seed del rol 'transportador' violaba el CHECK viejo y la
    aplicación no podía arrancar (bucle de reinicio). Tampoco se re-creaban los
    índices que V6 borra al reconstruir las tablas.
    """
    ahora = ahora_txt()
    with db_connection(commit=True) as conn:
        _crear_tablas(conn)
        _registrar_migracion_inicial(conn, ahora)
    _aplicar_migraciones_pendientes()
    with db_connection(commit=True) as conn:
        # Red de seguridad para BDs migradas: completa columnas e índices que
        # las migraciones antiguas pudieron dejar a medias por errores
        # "duplicate column" ignorados.
        _asegurar_columnas(conn)
        conn.executescript(INDEXES_SQL)
        _seed_usuarios(conn, ahora)
        _seed_config(conn)
    _migrar_secretos_desde_config()
    obtener_o_generar_receptores_secret()
    inicializar_receptores_db()
    limpiar_sesiones_expiradas()


def _aplicar_migraciones_pendientes():
    """
    Ejecuta archivos SQL de la carpeta database/migrations que aún no han sido
    aplicados. Cada archivo debe nombrarse con el patrón:
       V{version}_{nombre_descriptivo}.sql

    Las migraciones se ejecutan con las claves foráneas DESACTIVADAS: V6
    reconstruye ``usuarios`` y ``guias`` con DROP TABLE y, con FK activas, el
    DROP borraba en cascada sesiones y eventos y dejaba ``guias.creada_por`` en
    NULL (pérdida silenciosa de trazabilidad al actualizar).
    """
    if not os.path.isdir(MIGRATIONS_DIR):
        return
    conn = get_connection()
    try:
        # Modo autocommit + FK OFF: DDL como DROP TABLE ejecuta acciones en
        # cascada si las FK están activas (V6 borraba eventos y sesiones).
        # PRAGMA foreign_keys no tiene efecto dentro de una transacción, y la
        # conexión de Python abre una implícita al primer DML: por eso se pasa
        # a autocommit antes de desactivarlas.
        try:
            conn.isolation_level = None
            conn.execute("PRAGMA foreign_keys=OFF")
        except sqlite3.Error:
            pass
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "version INTEGER PRIMARY KEY, nombre TEXT NOT NULL, aplicada_en TEXT NOT NULL)")
        conn.commit()
        aplicadas = {
            r["version"]
            for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        def _version_de(nombre: str) -> int:
            return int(nombre.split("_", 1)[0][1:])

        archivos = []
        for f in os.listdir(MIGRATIONS_DIR):
            if not (f.startswith("V") and f.endswith(".sql")):
                continue
            try:
                archivos.append((_version_de(f), f))
            except (ValueError, IndexError):
                continue
        # ORDEN NUMÉRICO: sorted() de texto aplicaba V10 antes de V2.
        archivos.sort()

        for version, nombre in archivos:
            if version in aplicadas:
                continue
            ruta = os.path.join(MIGRATIONS_DIR, nombre)
            with open(ruta, "r", encoding="utf-8") as fh:
                sql = fh.read()
            try:
                # Algunas migraciones (V4/V5) terminan con PRAGMA foreign_keys=ON.
                # Se vuelve a desactivar antes de CADA archivo para que
                # reconstrucciones como la de V6 (DROP TABLE guias) no borren en
                # cascada los eventos ni vacíen creada_por.
                conn.execute("PRAGMA foreign_keys=OFF")
                conn.executescript(sql)
            except sqlite3.OperationalError as exc:
                msg = str(exc).lower()
                if not (
                    "duplicate column name" in msg
                    or "duplicate index name" in msg
                    or "already exists" in msg
                    or "duplicate table name" in msg
                ):
                    raise
            conn.execute(
                "INSERT OR REPLACE INTO schema_migrations(version, nombre, aplicada_en) VALUES (?, ?, ?)",
                (version, nombre, ahora_txt()),
            )
            conn.commit()
    finally:
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.Error:
            pass
        conn.close()


def limpiar_sesiones_expiradas():
    """Elimina sesiones cuya fecha de expiración ya pasó."""
    ahora = ahora_txt()
    with db_connection(commit=True) as conn:
        conn.execute("DELETE FROM sesiones WHERE expira < ?", (ahora,))


def get_config(clave: str, por_def: str = "") -> str:
    """Obtiene un valor de la tabla config."""
    with db_connection() as conn:
        r = conn.execute(
            "SELECT valor FROM config WHERE clave = ?", (clave,)
        ).fetchone()
        return r["valor"] if r else por_def


def set_config(clave: str, valor: str):
    """Inserta o actualiza un valor en config."""
    with db_connection(commit=True) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config(clave, valor) VALUES (?, ?)",
            (clave, str(valor)),
        )


def obtener_o_generar_receptores_secret() -> str:
    """
    Devuelve la clave maestra de cifrado de receptores.

    El valor vive en DATA_DIR/secretos.json, FUERA de la base de datos. Motivo:
    si un administrador puede descargar o copiar el archivo de datos (o si se
    filtra), no debe llevarse también la clave que descifra los datos personales.

    Compatibilidad: si una instalación anterior tenía la clave en la tabla
    `config`, se traslada al archivo de secretos y se borra de la base.

    Regla invariable: NUNCA hardcodear claves. 1 llamada → 1 valor persistido.
    """
    import secrets as _secrets

    from guias_coodescor.config import DATA_DIR, RECEPTORES_SECRET_KEY_NAME
    from guias_coodescor.core.paths import asegurar_secreto

    return asegurar_secreto(DATA_DIR, RECEPTORES_SECRET_KEY_NAME, lambda: _secrets.token_urlsafe(32))


def _migrar_secretos_desde_config() -> None:
    """
    Traslada a DATA_DIR/secretos.json los secretos que vivían en la tabla
    `config` y los elimina de la base de datos. Se ejecuta una sola vez por
    instalación (queda el marcador `secretos_en_archivo`).
    """
    import guias_coodescor.config as cfg
    from guias_coodescor.core.paths import escribir_secretos, leer_secretos

    if get_config("secretos_en_archivo", "") == "1":
        return

    marcadores = [
        "INSERT OR REPLACE INTO config(clave, valor) VALUES ('secretos_en_archivo', '1')"
    ]
    try:
        with db_connection(commit=True) as conn:
            pendientes = conn.execute(
                "SELECT clave, valor FROM config WHERE clave IN (?, ?)",
                (cfg.RECEPTORES_SECRET_KEY_NAME, cfg.CAPTCHA_SECRET_KEY_NAME),
            ).fetchall()
            existentes = [f for f in pendientes if f["valor"]]
            if existentes:
                secretos = leer_secretos(cfg.DATA_DIR)
                cambiados = [
                    f["clave"]
                    for f in existentes
                    if f["clave"] not in secretos
                ]
                for clave in cambiados:
                    secretos[clave] = next(f["valor"] for f in existentes if f["clave"] == clave)
                escribir_secretos(cfg.DATA_DIR, secretos)
                conn.execute(
                    "DELETE FROM config WHERE clave IN (?, ?)",
                    (cfg.RECEPTORES_SECRET_KEY_NAME, cfg.CAPTCHA_SECRET_KEY_NAME),
                )
            conn.execute(marcadores[0])
    except Exception:
        # Nunca impedir el arranque por esto: la clave antigua sigue en su sitio.
        return


def inicializar_receptores_db() -> None:
    """Crea tablas e índices en el archivo separado receptores.db.
    Idempotente: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
    """
    from guias_coodescor.database.connection import receptores_db_connection
    with receptores_db_connection(commit=True) as conn:
        conn.executescript(RECEPTORES_SCHEMA_SQL)
