import sqlite3
conn = sqlite3.connect(r'C:\ProgramData\Coodescor\Guias\guias.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM clientes')
print('Total clientes:', c.fetchone()[0])
c.execute('SELECT nit, razon_social, cliente_descubierto FROM clientes LIMIT 10')
for r in c.fetchall():
    print('  NIT={}, Razón={}, Descubierto={}'.format(r["nit"], r["razon_social"], r["cliente_descubierto"]))
c.execute('SELECT COUNT(*) FROM guias')
print('Total guias:', c.fetchone()[0])
c.execute('SELECT COUNT(*) FROM guias WHERE nit IS NOT NULL AND nit != ""')
print('Guias con NIT:', c.fetchone()[0])
# Check the FK relationship
c.execute('SELECT nit FROM guias WHERE nit IS NOT NULL AND nit != "" LIMIT 5')
for r in c.fetchall():
    nit = r["nit"]
    c2 = conn.cursor()
    c2.execute('SELECT nit, razon_social FROM clientes WHERE nit = ? COLLATE NOCASE', (nit,))
    match = c2.fetchone()
    if match:
        print('  Guia NIT {} -> Cliente: {}'.format(nit, match["razon_social"]))
    else:
        print('  Guia NIT {} -> NO ENCONTRADO en clientes'.format(nit))