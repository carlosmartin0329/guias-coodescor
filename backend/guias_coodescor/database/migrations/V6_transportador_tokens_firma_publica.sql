-- V6: Rol transportador propio + selector propio/externo + tokens firma pública sin login
-- Aplica cambios:
--  (a) usuarios.rol CHECK incluye 'transportador'
--  (b) guias agrega columnas tipo_transportador / transportador_asignado_id
--  (c) crea tabla entrega_tokens (UNO por guia, UN SOLO USO, link público /firma/<TOKEN>)
-- Ejecutado dentro de una transacción con PRAGMA foreign_keys=ON al final.
-- Rollback automático si algo falla.

BEGIN;

-- =========================================================================
-- (a) Recrear tabla 'usuarios' para agregar 'transportador' al CHECK(rol)
-- =========================================================================
CREATE TABLE usuarios_v6 (
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
INSERT INTO usuarios_v6 (id,usuario,nombre,pass_hash,sal,rol,activo,creado,ultima_sesion,intentos_fallidos,bloqueado_hasta)
SELECT id,usuario,nombre,pass_hash,sal,rol,activo,creado,ultima_sesion,intentos_fallidos,bloqueado_hasta FROM usuarios;
DROP TABLE usuarios;
ALTER TABLE usuarios_v6 RENAME TO usuarios;
-- Restaurar PK autoincrement (sqlite_sequence). En SQLite CREATE TABLE ... RENAME preserva rowid.

-- =========================================================================
-- (b) Recrear tabla 'guias' para agregar tipo_transportador / transportador_asignado_id
--     Incluye también nit / centro_operacion / prefijo (agregados en el sprint de autocompletado NIT)
-- =========================================================================
CREATE TABLE guias_v6 (
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
INSERT INTO guias_v6 (id,consecutivo,cliente,nit,centro_operacion,prefijo,ciudad,direccion,documentos,obs_ventas,
                     envio_directo_cedis,creada_por,creada_en,estado,anulada_motivo,anulada_por,anulada_en,
                     tipo_transportador,transportador_asignado_id)
SELECT id,consecutivo,cliente,nit,centro_operacion,prefijo,ciudad,direccion,documentos,obs_ventas,
       envio_directo_cedis,creada_por,creada_en,estado,anulada_motivo,anulada_por,anulada_en,
       NULL,NULL
FROM guias;
DROP TABLE guias;
ALTER TABLE guias_v6 RENAME TO guias;

-- =========================================================================
-- (c) Crear tabla entrega_tokens (link público de firma: 1 por guía, 1 uso)
-- =========================================================================
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

CREATE INDEX IF NOT EXISTS idx_entrega_tokens_token ON entrega_tokens(token);
CREATE INDEX IF NOT EXISTS idx_entrega_tokens_guia_id ON entrega_tokens(guia_id);
CREATE INDEX IF NOT EXISTS idx_guias_transportador_asignado_id ON guias(transportador_asignado_id);
CREATE INDEX IF NOT EXISTS idx_guias_tipo_transportador ON guias(tipo_transportador);

COMMIT;
