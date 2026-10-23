CREATE TABLE IF NOT EXISTS clientes_contactos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nit_cliente TEXT NOT NULL,
  nombre TEXT NOT NULL,
  telefono TEXT,
  cedula TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
