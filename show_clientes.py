import sqlite3
conn = sqlite3.connect(r'C:\ProgramData\Coodescor\Guias\guias.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Schema
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='clientes'")
print('=== SCHEMA clientes ===')
print(c.fetchone()[0])
print()

# Count
c.execute('SELECT COUNT(*) FROM clientes')
print('Total clientes: {}'.format(c.fetchone()[0]))
print()

# All clients
c.execute('SELECT nit, razon_social, direccion, ciudad, telefono, email, cliente_descubierto FROM clientes ORDER BY cliente_descubierto ASC, razon_social ASC')
print('=== TODOS LOS CLIENTES ===')
for r in c.fetchall():
    print('NIT={} | Razón={} | Dir={} | Ciudad={} | Tel={} | Email={} | Descubierto={}'.format(
        r["nit"], r["razon_social"][:50], r["direccion"] or "-", r["ciudad"] or "-", 
        r["telefono"] or "-", r["email"] or "-", r["cliente_descubierto"]))