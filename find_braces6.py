#!/usr/bin/env python3
import tokenize
import io

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

tokens = tokenize.generate_tokens(io.StringIO(content).readline)
depth = 0
path_start_depth = None
in_paths = False
start_line = 51
end_line = 843

for tok in tokens:
    if tok.type == tokenize.OP:
        if tok.string == '{':
            if path_start_depth is not None:
                path_start_depth += 1
            depth += 1
        elif tok.string == '}':
            if path_start_depth is not None:
                path_start_depth -= 1
            depth -= 1
    if tok.start[0] == start_line and tok.type == tokenize.OP and tok.string == '{':
        path_start_depth = 0
        print(f"PATHS opening brace at line {tok.start[0]}, depth track starts")
    if path_start_depth == 0 and tok.start[0] > start_line and tok.type == tokenize.OP and tok.string == '}':
        print(f"PATHS closing brace at line {tok.start[0]}")
        break
    if tok.start[0] == end_line:
        print(f"Reached end of PATHS region. path_start_depth = {path_start_depth}")
        break

print(f"\nFinal path_start_depth: {path_start_depth}")
print(f"Final overall depth: {depth}")
