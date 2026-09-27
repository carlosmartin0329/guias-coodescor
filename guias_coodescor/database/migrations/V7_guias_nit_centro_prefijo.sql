-- ============================================================================
-- Migración V7 · Garantiza columnas nit / centro_operacion / prefijo en tabla guias
-- Corrige instalaciones donde la migración V6 original se ejecutó antes de la
-- adición de estos 3 campos al sprint de autocompletado NIT.
-- El runner de migraciones ignora 'duplicate column name', por lo que es seguro
-- ejecutarla incluso si las columnas ya existen (nuevas instalaciones o V6 corregida).
-- ============================================================================

PRAGMA foreign_keys=off;

ALTER TABLE guias ADD COLUMN nit TEXT;
ALTER TABLE guias ADD COLUMN centro_operacion TEXT;
ALTER TABLE guias ADD COLUMN prefijo TEXT CHECK (prefijo IS NULL OR prefijo IN ('FV','TB','PD','TR'));

CREATE INDEX IF NOT EXISTS idx_guias_nit ON guias(nit);
CREATE INDEX IF NOT EXISTS idx_guias_centro_operacion ON guias(centro_operacion);
CREATE INDEX IF NOT EXISTS idx_guias_prefijo ON guias(prefijo);

PRAGMA foreign_keys=on;
