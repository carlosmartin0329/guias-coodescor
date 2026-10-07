#!/usr/bin/env python3
with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'ErrorResponse' in line and any(c in line for c in ['"401"', '"403"', '"400"']):
        stripped = line.rstrip()
        closing = 0
        for ch in reversed(stripped):
            if ch == '}':
                closing += 1
            else:
                break
        if closing < 4:
            print(f'Line {i}: {closing} closing braces | {line.strip()[-80:]}')
