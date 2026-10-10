import sys
sys.path.insert(0, r'D:\Users\57323\Downloads\guias coodescor')
from guias_coodescor.services.clientes_service import buscar_clientes

# Test with NITs from the Excel
test_nits = ['900966241', '73143333', '800199231-4', '890900321-1', '900123456-7']
for nit in test_nits:
    resultados = buscar_clientes(nit, limite=3)
    print('Buscar "{}": {} resultados'.format(nit, len(resultados)))
    for r in resultados:
        print('  NIT={}, Razón={}, Dir={}, Ciudad={}'.format(r.get('nit'), r.get('razon_social')[:40], r.get('direccion'), r.get('ciudad')))