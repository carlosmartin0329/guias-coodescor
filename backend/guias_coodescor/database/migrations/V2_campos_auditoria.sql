-- ============================================================================
-- Migración V2 · Agrega campos de auditoría a la tabla guias
-- Aplica solo si no existen (mantiene compatibilidad con la antigua DB).
-- ============================================================================

-- Campos agregados en la reestructuración modular para trazabilidad de anulación.
ALTER TABLE guias ADD COLUMN anulada_por INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE guias ADD COLUMN anulada_en TEXT;

-- Campos agregados en la tabla usuarios para control de seguridad (bloqueo por intentos).
ALTER TABLE usuarios ADD COLUMN ultima_sesion TEXT;
ALTER TABLE usuarios ADD COLUMN intentos_fallidos INTEGER NOT NULL DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN bloqueado_hasta TEXT;

-- Campos agregados en sesiones y eventos para auditoría de IP/dispositivo.
ALTER TABLE sesiones ADD COLUMN ip TEXT;
ALTER TABLE sesiones ADD COLUMN user_agent TEXT;
ALTER TABLE eventos ADD COLUMN ip TEXT;

-- Recrear índices (si no existen) para acelerar búsquedas.
CREATE INDEX IF NOT EXISTS idx_guias_estado ON guias(estado);
CREATE INDEX IF NOT EXISTS idx_guias_creada_en ON guias(creada_en);
CREATE INDEX IF NOT EXISTS idx_eventos_guia_id ON eventos(guia_id);
CREATE INDEX IF NOT EXISTS idx_sesiones_expira ON sesiones(expira);
