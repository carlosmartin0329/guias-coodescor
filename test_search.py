import sys
sys.path.insert(0, r'D:\Users\57323\Downloads\guias coodescor')
from guias_coodescor.core.utils import normalizar_nit
from guias_coodescor.services.clientes_service import buscar_clientes

# Test the normalization
test_nits = ["800199231-4", "8001992314", "890900321-1", "8909003211", "900123456-7", "9001234567"]
for nit in test_nits:
    norm = normalizar_nit(nit)
    print("Original: {} -> Normalizado: {}".format(nit, norm))

print("\n--- Testing buscar_clientes ---")
# Test with dash format (like in guias)
for nit in ["800199231-4", "890900321-1", "900123456-7"]:
    resultados = buscar_clientes(nit, limite=5)
    print("\nBuscar '{}': {} resultados".format(nit, len(resultados)))
    for r in resultados:
        print("  NIT={}, Razón={}".format(r.get("nit"), r.get("razon_social")))

# Test with normalized format (like in clientes)
for nit in ["8001992314", "8909003211", "9001234567"]:
    resultados = buscar_clientes(nit, limite=5)
    print("\nBuscar '{}': {} resultados".format(nit, len(resultados)))
    for r in resultados:
        print("  NIT={}, Razón={}".format(r.get("nit"), r.get("razon_social")))