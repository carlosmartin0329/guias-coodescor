#!/usr/bin/env python3
with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Try to compile and get syntax error location
try:
    compile(content, 'openapi_spec.py', 'exec')
    print("File compiles OK!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    print(f"Text: {e.text}")
    print(f"Offset: {e.offset}")
