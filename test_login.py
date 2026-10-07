import urllib.request
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

r = urllib.request.urlopen('http://127.0.0.1:8000/login')
html = r.read().decode('utf-8')

# Find forms
forms = re.findall(r'<form[^>]*>.*?</form>', html, re.DOTALL)
for i, f in enumerate(forms):
    print(f'FORM {i}:')
    print(f[:3000])
    print('---')

# Also check for input fields
inputs = re.findall(r'<input[^>]*>', html)
for inp in inputs:
    print(inp)