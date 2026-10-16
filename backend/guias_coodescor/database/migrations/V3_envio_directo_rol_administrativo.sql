-- ============================================================================
-- Migración V3 · Envío directo a CEDIS, nuevo rol 'administrativo' y 4 ventas
-- Aplica solo si no existen (mantiene compatibilidad con bases antiguas).
-- ============================================================================

-- 1) Agregar bandera de envio_directo_cedis en guias
ALTER TABLE guias ADD COLUMN envio_directo_cedis INTEGER NOT NULL DEFAULT 0 CHECK(envio_directo_cedis IN (0,1));

-- 2) Actualizar la restricción CHECK de roles en usuarios para admitir 'administrativo'
--    SQLite no permite ALTER COLUMN sobre CHECKs, así que se recrea la tabla si es necesario.
--    Nota: en la mayoría de casos la tabla ya fue recreada por models.py; si usa una DB antigua,
--    ejecute manualmente el dump y reload o deje que models.py valide al insertar.

-- 3) Nuevos tipos de evento: 'envio_directo_cedis' ya está dentro del CHECK actualizado en models.py;
--    para bases viejas, los nuevos eventos se insertan ok, pero el CHECK antiguo podría bloquearlos.
--    Si recibe "CHECK constraint failed: eventos", recrear la tabla eventos:
--    PRAGMA foreign_keys=off;
--    CREATE TABLE eventos_nuevo (... CHECK(tipo IN (...,'envio_directo_cedis')));
--    INSERT INTO eventos_nuevo SELECT * FROM eventos;
--    DROP TABLE eventos;
--    ALTER TABLE eventos_nuevo RENAME TO eventos;
--    PRAGMA foreign_keys=on;

-- 4) Insertar nuevos usuarios por defecto (solo si no existen)
--    (administrativo y ventas 2-4). Las claves aquí son de ejemplo; cámbielas en el panel.
--    El hash PBKDF2 no se calcula aquí; use el panel admin del sistema para crearlos
--    con clave real o deje que models.py → _seed_usuarios() lo haga al iniciar.
