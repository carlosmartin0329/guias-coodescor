#!/usr/bin/env python3
with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if 'ErrorResponse' in stripped and ("401" in stripped or "403" in stripped or "400" in stripped):
        # Check ending: should end with "}}}},  or }}}},
        if stripped.endswith('}}},') or stripped.endswith('}}}'):
            print(f'Line {i}: BAD ending (3 braces) | {stripped[-100:]}')
