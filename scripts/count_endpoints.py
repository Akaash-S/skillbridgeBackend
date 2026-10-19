import os
import re

routes_dir = 'backend/app/routes'
all_endpoints = []

# First check __init__.py
with open('backend/app/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()
    for m in re.finditer(r'@app\.route\(([\'\"][^\'\"]+[\'\"])((?:,\s*methods=\[[^\]]+\])?)', content):
        all_endpoints.append(('__init__.py', m.group(1).strip('\'"'), m.group(2).strip()))

# Check all route files
for fname in sorted(os.listdir(routes_dir)):
    if fname.endswith('.py'):
        with open(os.path.join(routes_dir, fname), 'r', encoding='utf-8') as f:
            content = f.read()
            for m in re.finditer(r'@\w+_bp\.route\(([\'\"][^\'\"]*[\'\"])((?:,\s*methods=\[[^\]]+\])?)', content):
                all_endpoints.append((fname, m.group(1).strip('\'"'), m.group(2).strip()))

print(f"Total endpoint decorators found: {len(all_endpoints)}")
for ep in all_endpoints:
    print(ep)
