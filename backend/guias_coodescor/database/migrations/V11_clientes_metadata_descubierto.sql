-- ============================================================================
-- V11 · Completa columnas de clientes introducidas en el sprint de
--       autocompletado NIT. Solo estaban en el CREATE TABLE de models.py y
--       ninguna migración las agregaba, así que las instalaciones anteriores
--       fallaban al guardar clientes (INSERT/UPDATE con columnas inexistentes).
--
--       El runner ignora el error "duplicate column name", por lo que es
--       seguro ejecutarla también en bases nuevas.
-- ============================================================================

ALTER TABLE clientes ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}';
ALTER TABLE clientes ADD COLUMN cliente_descubierto INTEGER NOT NULL DEFAULT 0;
ALTER TABLE clientes ADD COLUMN contacto TEXT;
ALTER TABLE clientes ADD COLUMN forma_pago_default TEXT;
ALTER TABLE clientes ADD COLUMN observaciones TEXT;

CREATE INDEX IF NOT EXISTS idx_clientes_nit ON clientes(nit);
CREATE INDEX IF NOT EXISTS idx_guias_transportador_asignado_id ON guias(transportador_asignado_id);
CREATE INDEX IF NOT EXISTS idx_guias_tipo_transportador ON guias(tipo_transportador);
CREATE INDEX IF NOT EXISTS idx_entrega_tokens_token ON entrega_tokens(token);
CREATE INDEX IF NOT EXISTS idx_entrega_tokens_guia_id ON entrega_tokens(guia_id);
