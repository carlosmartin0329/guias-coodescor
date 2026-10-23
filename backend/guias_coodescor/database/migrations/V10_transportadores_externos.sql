-- ============================================================================
-- Migración V10 · Tabla para almacenar datos de transportadores externos
-- Esto permite autocompletado y persistencia de la información de transportadores
-- externos que son registrados por el usuario administrativo.
-- ============================================================================

CREATE TABLE IF NOT EXISTS transportadores_externos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre TEXT NOT NULL,
  cc TEXT NOT NULL,
  telefono TEXT NOT NULL,
  vehiculo TEXT,
  placa TEXT,
  flete TEXT,
  observaciones TEXT,
  creado_por INTEGER,
  creado_rol TEXT,
  creado_en TEXT NOT NULL,
  actualizado_en TEXT NOT NULL,
  activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
  FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_transportadores_externos_nombre ON transportadores_externos(nombre);
CREATE INDEX IF NOT EXISTS idx_transportadores_externos_cc ON transportadores_externos(cc);
CREATE INDEX IF NOT EXISTS idx_transportadores_externos_placa ON transportadores_externos(placa);
CREATE INDEX IF NOT EXISTS idx_transportadores_externos_telefono ON transportadores_externos(telefono);
