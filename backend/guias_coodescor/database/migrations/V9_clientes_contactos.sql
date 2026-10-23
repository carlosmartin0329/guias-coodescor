CREATE TABLE IF NOT EXISTS clientes_contactos (
  id SERIAL PRIMARY KEY,
  nit_cliente VARCHAR(60) NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  telefono VARCHAR(50),
  cedula VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW()
);
