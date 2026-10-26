-- ============================================================================
-- Migración V12 · Agrega el tipo de evento 'captura_reclamo' al CHECK de eventos
-- Permite registrar nombre/cédula/teléfono y firma de la persona que reclama
-- sin cambiar el estado de la guía ni cerrar la entrega.
-- SQLite no permite modificar un CHECK con ALTER TABLE: se recrea la tabla.
-- ============================================================================

PRAGMA foreign_keys=off;

CREATE TABLE IF NOT EXISTS eventos_nuevo (
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

INSERT OR IGNORE INTO eventos_nuevo(id, guia_id, tipo, usuario_id, usuario, rol, en, dispositivo, ip, datos)
SELECT id, guia_id, tipo, usuario_id, usuario, rol, en, dispositivo, ip, datos FROM eventos;

DROP TABLE IF EXISTS eventos;
ALTER TABLE eventos_nuevo RENAME TO eventos;

CREATE INDEX IF NOT EXISTS idx_eventos_guia_id ON eventos(guia_id);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON eventos(tipo);
CREATE INDEX IF NOT EXISTS idx_eventos_en ON eventos(en);

PRAGMA foreign_keys=on;
