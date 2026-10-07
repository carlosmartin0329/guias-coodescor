#!/usr/bin/env python3
import ast

with open('guias_coodescor/api/openapi_spec.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
start = None
end = None
for i, line in enumerate(lines, 1):
    if 'PATHS: dict = {' in line:
        start = i
    if 'COMPONENTS = {' in line and start:
        end = i
        break

# Track bracket depth using Python-aware method
# We need to skip braces inside strings
depth = 0
for i in range(start - 1, end):
    line = lines[i]
    # Simple approach: track if we're inside a string
    in_str = False
    str_char = None
    for j, ch in enumerate(line):
        if in_str:
            if ch == str_char:
                in_str = False
                str_char = None
        else:
            if ch in ('"', "'"):
                # Check for triple quotes
                if line[j:j+3] in ('"""', "'''"):
                    in_str = True
                    str_char = line[j:j+3]
                else:
                    in_str = True
                    str_char = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
    if i + 1 == start:
        print(f"Line {i+1}: depth={depth}")
    if depth == 0 and i + 1 > start:
        print(f"PATHS dict closes at line {i+1}, depth={depth}")
        print(f"Line content: {line.strip()[:80]}")
        break
else:
    print(f"Never closes. Final depth at line {end}: {depth}")
    # Check what happens around the end
    for i in range(end - 5, end):
        print(f"Line {i+1}: depth at end of line={depth}, content: {lines[i].strip()[:80]}")
