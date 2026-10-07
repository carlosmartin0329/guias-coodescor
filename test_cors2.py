import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Test CORS preflight
req = urllib.request.Request('http://127.0.0.1:8000/api/clientes/buscar?q=test&limite=5', method='OPTIONS')
req.add_header('Origin', 'https://ostensively-nonchalky-kenya.ngrok-free.dev')
req.add_header('Access-Control-Request-Method', 'GET')
req.add_header('Access-Control-Request-Headers', 'Content-Type')

try:
    r = urllib.request.urlopen(req)
    print('OPTIONS Status:', r.status)
    print('OPTIONS Headers:')
    for k, v in r.headers.items():
        if 'access-control' in k.lower() or 'origin' in k.lower() or 'vary' in k.lower():
            print(f'  {k}: {v}')
except urllib.error.HTTPError as e:
    print('OPTIONS HTTP Error:', e.code)
    for k, v in e.headers.items():
        if 'access-control' in k.lower() or 'origin' in k.lower() or 'vary' in k.lower():
            print(f'  {k}: {v}')
except Exception as e:
    print('OPTIONS Error:', e)

print()

# Test actual GET with Origin header
req = urllib.request.Request('http://127.0.0.1:8000/api/clientes/buscar?q=900&limite=5')
req.add_header('Origin', 'https://ostensively-nonchalky-kenya.ngrok-free.dev')

try:
    r = urllib.request.urlopen(req)
    print('GET Status:', r.status)
    print('GET Headers:')
    for k, v in r.headers.items():
        if 'access-control' in k.lower() or 'origin' in k.lower() or 'vary' in k.lower() or 'content-type' in k.lower():
            print(f'  {k}: {v}')
    print('Body preview:', r.read().decode('utf-8')[:200])
except urllib.error.HTTPError as e:
    print('GET HTTP Error:', e.code)
    for k, v in e.headers.items():
        if 'access-control' in k.lower() or 'origin' in k.lower() or 'vary' in k.lower() or 'content-type' in k.lower():
            print(f'  {k}: {v}')
    print('Body:', e.read().decode('utf-8')[:500])
except Exception as e:
    print('GET Error:', e)