import sqlite3

conn = sqlite3.connect(r"C:\ProgramData\Coodescor\Guias\guias.db")
cursor = conn.cursor()
tables = cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()
for t in tables:
    name = t[0]
    print(f"\n=== Tabla: {name} ===")
    cols = cursor.execute(f"PRAGMA table_info(\"{name}\")").fetchall()
    for c in cols:
        print(f"  {c[1]} ({c[2]}) {'PK' if c[5] else ''}")
    count = cursor.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    print(f"  Total filas: {count}")
conn.close()
