import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Test OPTIONS with Origin header
req = urllib.request.Request('http://127.0.0.1:8000/api/clientes/buscar?q=test&limite=5', method='OPTIONS')
req.add_header('Origin', 'https://ostensively-nonchalky-kenya.ngrok-free.dev')
req.add_header('Access-Control-Request-Method', 'GET')
req.add_header('Access-Control-Request-Headers', 'Content-Type')

try:
    r = urllib.request.urlopen(req)
    print('OPTIONS Status:', r.status)
    print('OPTIONS Headers:')
    for k, v in r.headers.items():
        print(f'  {k}: {v}')
except urllib.error.HTTPError as e:
    print('OPTIONS HTTP Error:', e.code)
    for k, v in e.headers.items():
        print(f'  {k}: {v}')
except Exception as e:
    print('OPTIONS Error:', e)