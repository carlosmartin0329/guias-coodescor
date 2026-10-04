-- ============================================================================
-- Migración V8 · Auditoría del módulo de administración de la base de datos
-- ----------------------------------------------------------------------------
-- Registra toda operación hecha desde el panel Admin → Base de datos: qué se
-- tocó, quién, desde qué IP y con qué valores antes y después.
--
-- Se crea con una clave foránea ON DELETE SET NULL hacia usuarios para que
-- borrar un usuario no rompa el historial, y se deja sin clave foránea hacia
-- tablas de negocio porque las filas se pueden eliminar en cascada (al borrar
-- una guía se borran sus eventos) y el rastro de auditoría debe sobrevivir.
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    en          TEXT    NOT NULL,
    usuario_id  INTEGER,
    usuario     TEXT,
    rol         TEXT,
    ip          TEXT,
    accion      TEXT    NOT NULL,
    tabla       TEXT,
    clave       TEXT,
    resumen     TEXT,
    detalle     TEXT,
    filas_afectadas INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_auditoria_en ON admin_auditoria(en);
CREATE INDEX IF NOT EXISTS idx_admin_auditoria_usuario ON admin_auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_admin_auditoria_accion ON admin_auditoria(accion);
CREATE INDEX IF NOT EXISTS idx_admin_auditoria_tabla ON admin_auditoria(tabla);