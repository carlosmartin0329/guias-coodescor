#!/usr/bin/env python3
import tokenize
import io

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

tokens = tokenize.generate_tokens(io.StringIO(content).readline)
depth = 0
for tok in tokens:
    if tok.type == tokenize.OP and tok.string in ('{', '}'):
        old = depth
        if tok.string == '{':
            depth += 1
        else:
            depth -= 1
        # Only show first 100 depth changes and any negative
        if depth < 0:
            print(f"NEGATIVE at line {tok.start[0]}: {tok.string} -> depth {old} -> {depth}")

# Now try ast parse to get the real error
import ast
try:
    ast.parse(content)
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"Text: {e.text}")
