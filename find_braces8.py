#!/usr/bin/env python3
import tokenize
import io

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

tokens = tokenize.generate_tokens(io.StringIO(content).readline)
depth = 0
prev_depth = 0

for tok in tokens:
    if tok.type == tokenize.OP and tok.string in ('{', '}'):
        old = depth
        if tok.string == '{':
            depth += 1
        else:
            depth -= 1
        if depth != prev_depth:
            print(f"Line {tok.start[0]} col {tok.start[1]}: {tok.string} -> depth {old} -> {depth}")
            prev_depth = depth
        if depth < 0:
            print(f"NEGATIVE depth at line {tok.start[0]}")
            break

print(f"\nFinal depth: {depth}")
print(f"Tokenize done.")
