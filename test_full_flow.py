import urllib.request
import urllib.parse
import http.cookiejar
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Get login page
r = opener.open('http://127.0.0.1:8000/login')
html = r.read().decode('utf-8')

# Extract captcha token
csrf_match = re.search(r'name="captcha_token" id="captcha-token" value="([^"]+)"', html)
captcha_token = csrf_match.group(1) if csrf_match else ''

# Extract captcha answer - we need to parse the SVG
# The captcha is a 6-character code in the SVG
# Let's try to extract it from the SVG
svg_match = re.search(r'<svg[^>]*class="captcha-image"[^>]*>(.*?)</svg>', html, re.DOTALL)
if svg_match:
    svg = svg_match.group(1)
    # The captcha text is in the SVG - look for text elements
    text_matches = re.findall(r'<text[^>]*>([^<]+)</text>', svg)
    print('SVG text elements:', text_matches)
    # Usually the captcha is in a specific text element
    # Let's look for the pattern
    captcha_code = ''.join(text_matches)
    print('Possible captcha:', captcha_code)

# Try API login with captcha
api_login_url = 'http://127.0.0.1:8000/api/login'
data = urllib.parse.urlencode({
    'usuario': 'ventas',
    'clave': 'ventas123',
    'captcha_respuesta': captcha_code if captcha_code else 'ABCDEF',
    'captcha_token': captcha_token
}).encode()

req = urllib.request.Request(api_login_url, data=data, method='POST')
req.add_header('Content-Type', 'application/x-www-form-urlencoded')
req.add_header('Origin', 'https://ostensively-nonchalky-kenya.ngrok-free.dev')

try:
    r = opener.open(req)
    print('Login API status:', r.status)
    print('Login response:', r.read().decode('utf-8')[:500])
    
    # Now test the autocomplete API
    r = opener.open('http://127.0.0.1:8000/api/clientes/buscar?q=800199231-4&limite=5')
    print('\nAutocomplete API status:', r.status)
    print('Autocomplete response:', r.read().decode('utf-8')[:1000])
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.code)
    print('Response:', e.read().decode('utf-8'))
except Exception as e:
    print('Error:', e)