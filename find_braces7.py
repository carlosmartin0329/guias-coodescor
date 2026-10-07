#!/usr/bin/env python3
import tokenize
import io

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

tokens = tokenize.generate_tokens(io.StringIO(content).readline)
depth = 0
start_line = 51

for tok in tokens:
    if tok.type == tokenize.OP and tok.string in ('{', '}'):
        if tok.start[0] >= start_line:
            old = depth
            if tok.string == '{':
                depth += 1
            else:
                depth -= 1
            if tok.start[0] <= 90:
                print(f"Line {tok.start[0]}: {tok.string} -> depth {old} -> {depth}")
