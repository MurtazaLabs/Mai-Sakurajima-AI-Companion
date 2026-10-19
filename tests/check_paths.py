import os
import re
import sys

sys.path.insert(0, r'E:\Mai_ai')

for root, dirs, files in os.walk(r'E:\Mai_ai'):
    if any(x in root for x in ['venv', '__pycache__', '.git', '.opencode', 'node_modules', 'mai_env']):
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            rel = os.path.relpath(path, r'E:\Mai_ai')
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                for i, line in enumerate(content.split('\n'), 1):
                    if re.search(r'[CDE]:\\\\', line) and 'test' not in path.lower() and 'example' not in path.lower():
                        print(f'{rel}:{i}: {line.strip()[:120]}')
            except:
                pass