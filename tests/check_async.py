import os
import sys

sys.path.insert(0, r'E:\Mai_ai')

print('=== CHECKING ASYNC/AWAIT PATTERNS ===')

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
                
                if 'async def' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'time.sleep(' in line and 'await asyncio.sleep' not in content:
                            print(f'SLEEP_IN_ASYNC: {rel}:{i}: {line.strip()[:80]}')
                        if 'requests.get' in line and 'await' not in line and 'aiohttp' not in content:
                            print(f'BLOCKING_HTTP: {rel}:{i}: {line.strip()[:80]}')
                        if 'requests.post' in line and 'await' not in line and 'aiohttp' not in content:
                            print(f'BLOCKING_HTTP_POST: {rel}:{i}: {line.strip()[:80]}')
                            
            except:
                pass

print('Done checking async patterns.')