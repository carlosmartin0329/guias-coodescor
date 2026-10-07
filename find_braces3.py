#!/usr/bin/env python3
with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines, 1):
    stripped = line.rstrip()
    if 'ErrorResponse' in stripped:
        # Count closing braces at end (before comma or whitespace)
        end_part = stripped.split('ErrorResponse')[-1]
        braced = 0
        for ch in reversed(stripped):
            if ch == '}':
                braced += 1
            elif ch == ',':
                continue
            else:
                break
        if braced != 4:
            print(f'Line {i}: {braced} closing braces | {stripped[-80:]}')
