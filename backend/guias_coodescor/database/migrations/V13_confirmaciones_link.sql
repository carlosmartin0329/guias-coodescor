-- ============================================================================
-- Migración V13 · Confirmaciones externas gratuitas (Google Apps Script)
-- Guarda el link emitido por Ventas/Administrativo y las confirmaciones que
-- llegan desde el formulario público. No modifica eventos ni estados.
-- ============================================================================

CREATE TABLE IF NOT EXISTS confirmaciones_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guia_id INTEGER NOT NULL UNIQUE,
    token TEXT UNIQUE NOT NULL,
    link TEXT NOT NULL,
    creado_por INTEGER,
    creado_rol TEXT,
    creado_en TEXT NOT NULL,
    expira_en TEXT NOT NULL,
    confirmacion_id TEXT UNIQUE,
    fecha_confirmacion TEXT,
    nombre TEXT,
    observaciones TEXT,
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','aplicada','duplicada','error')),
    aplicado_en TEXT,
    detalle TEXT,
    FOREIGN KEY (guia_id) REFERENCES guias(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_confirmaciones_link_estado
    ON confirmaciones_link(estado);
