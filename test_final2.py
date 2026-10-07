import urllib.request
import urllib.parse
import http.cookiejar
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Get captcha from API - this gives us SVG and token that match
r = opener.open('http://127.0.0.1:8000/api/captcha/nuevo')
data = json.loads(r.read().decode())
captcha_token = data['token']
svg = data['svg']
print('Token:', captcha_token[:30])

# Extract captcha code from the SVG returned by API
svg_match = re.search(r'<svg[^>]*class="captcha-image"[^>]*>(.*?)</svg>', svg, re.DOTALL)
captcha_code = ''
if svg_match:
    svg_inner = svg_match.group(1)
    text_matches = re.findall(r'<text[^>]*>([^<]+)</text>', svg_inner)
    captcha_code = ''.join(text_matches)
print('Captcha code from API SVG:', captcha_code)

# Login with the API token and extracted code
login_data = json.dumps({
    'usuario': 'ventas',
    'clave': 'ventas123',
    'captcha_respuesta': captcha_code,
    'captcha_token': captcha_token
}).encode()

req = urllib.request.Request('http://127.0.0.1:8000/api/login', data=login_data, method='POST')
req.add_header('Content-Type', 'application/json')
r = opener.open(req)
print('Login:', r.status, r.read().decode())

# Now test autocomplete
r = opener.open('http://127.0.0.1:8000/api/clientes/buscar?q=800199231-4&limite=5')
print('Autocomplete:', r.status, r.read().decode())