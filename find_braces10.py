#!/usr/bin/env python3
import ast

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

try:
    ast.parse(content)
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"Text: {e.text!r}")
    print(f"Offset: {e.offset}")
