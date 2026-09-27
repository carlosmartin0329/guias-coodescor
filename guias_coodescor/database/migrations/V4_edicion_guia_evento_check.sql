-- ============================================================================
-- Migración V4 · Agrega tipo de evento 'edicion_guia' al CHECK constraint de eventos
-- Requerido para que funcione la funcionalidad de edición de guías (auditoría).
-- SQLite NO permite ALTER TABLE modificar CHECK constraints, así que recreamos la tabla.
-- ============================================================================

PRAGMA foreign_keys=off;

CREATE TABLE IF NOT EXISTS eventos_nuevo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guia_id INTEGER NOT NULL,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('creacion','recepcion_admin','envio_directo_cedis','control_cedis','entrega_transporte','entrega_cliente','anular','edicion_guia')),
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

INSERT OR IGNORE INTO eventos_nuevo(id, guia_id, tipo, usuario_id, usuario, rol, en, dispositivo, ip, datos)
SELECT id, guia_id, tipo, usuario_id, usuario, rol, en, dispositivo, ip, datos FROM eventos;

DROP TABLE IF EXISTS eventos;
ALTER TABLE eventos_nuevo RENAME TO eventos;

CREATE INDEX IF NOT EXISTS idx_eventos_guia_id ON eventos(guia_id);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON eventos(tipo);
CREATE INDEX IF NOT EXISTS idx_eventos_en ON eventos(en);

PRAGMA foreign_keys=on;
