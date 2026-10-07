import sys
sys.path.insert(0, r'D:\Users\57323\Downloads\guias coodescor')
from guias_coodescor.services.clientes_service import buscar_clientes

# Test prefix search
print("--- Prefix search ---")
resultados = buscar_clientes("800199", limite=5)
print("Buscar '800199': {} resultados".format(len(resultados)))
for r in resultados:
    print("  NIT={}, Razón={}".format(r.get("nit"), r.get("razon_social")))

# Test razon social search
print("\n--- Razón social search ---")
resultados = buscar_clientes("FARMACIA", limite=5)
print("Buscar 'FARMACIA': {} resultados".format(len(resultados)))
for r in resultados:
    print("  NIT={}, Razón={}".format(r.get("nit"), r.get("razon_social")))

# Test ciudad search
print("\n--- Ciudad search ---")
resultados = buscar_clientes("BOGOTA", limite=5)
print("Buscar 'BOGOTA': {} resultados".format(len(resultados)))
for r in resultados:
    print("  NIT={}, Razón={}, Ciudad={}".format(r.get("nit"), r.get("razon_social"), r.get("ciudad")))

# Test telefono search
print("\n--- Teléfono search ---")
resultados = buscar_clientes("310", limite=5)
print("Buscar '310': {} resultados".format(len(resultados)))
for r in resultados:
    print("  NIT={}, Razón={}, Tel={}".format(r.get("nit"), r.get("razon_social"), r.get("telefono")))

# Test empty query
print("\n--- Empty query ---")
resultados = buscar_clientes("", limite=5)
print("Buscar '': {} resultados".format(len(resultados)))
for r in resultados[:3]:
    print("  NIT={}, Razón={}".format(r.get("nit"), r.get("razon_social")))