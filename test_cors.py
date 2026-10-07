import urllib.request
import urllib.parse
import http.cookiejar
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Login first
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Get CSRF token from login page
r = opener.open('http://127.0.0.1:8000/login')
html = r.read().decode('utf-8')
print('Login page length:', len(html))

# Check for form fields
csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
csrf = csrf_match.group(1) if csrf_match else ''
print('CSRF:', csrf[:20] if csrf else 'NOT FOUND')

# Check for username/password field names
user_match = re.search(r'name="([^"]*user[^"]*)"', html)
pass_match = re.search(r'name="([^"]*pass[^"]*)"', html)
print('User field:', user_match.group(1) if user_match else 'NOT FOUND')
print('Pass field:', pass_match.group(1) if pass_match else 'NOT FOUND')

# Try with common field names
for user_field in ['usuario', 'username', 'user', 'email']:
    for pass_field in ['password', 'pass', 'pwd']:
        data = urllib.parse.urlencode({user_field: 'ventas', pass_field: 'ventas123', 'csrf_token': csrf}).encode()
        req = urllib.request.Request('http://127.0.0.1:8000/login', data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        try:
            r = opener.open(req)
            print(f'Login with {user_field}/{pass_field}: status={r.status}')
            if r.status == 200 or r.status == 303:
                # Now test the API
                r = opener.open('http://127.0.0.1:8000/api/clientes/buscar?q=900&limite=5')
                print('API Status:', r.status)
                print('Headers:', dict(r.headers))
                print('Body:', r.read().decode('utf-8')[:500])
                sys.exit(0)
        except urllib.error.HTTPError as e:
            print(f'Login with {user_field}/{pass_field}: HTTP {e.code}')
        except Exception as e:
            print(f'Login with {user_field}/{pass_field}: {e}')

print('All login attempts failed')