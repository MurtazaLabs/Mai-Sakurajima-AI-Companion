import sys, os, re
sys.path.insert(0, r'E:\Mai_ai')

print('=== SCANNING FOR SECURITY ISSUES ===')

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
                
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    # Check for hardcoded credentials/secrets
                    if re.search(r'(password|secret|apikey|token)\s*=\s*[\'"][\w\-]{8,}[\'"]', line, re.I) and 'test' not in path.lower() and 'example' not in path.lower():
                        print(f'CREDENTIAL: {rel}:{i}: {line.strip()[:100]}')
                    
                    # Check for hardcoded IPs/URLs
                    if re.search(r'https?://\d+\.\d+\.\d+\.\d+', line) and 'test' not in path.lower() and 'example' not in path.lower():
                        print(f'HARDCODED_IP: {rel}:{i}: {line.strip()[:100]}')
                    
                    # Check for eval/exec usage
                    if re.search(r'\b(eval|exec)\s*\(', line) and 'test' not in path.lower():
                        print(f'EVAL_EXEC: {rel}:{i}: {line.strip()[:100]}')
                    
            except Exception as e:
                pass

print('Done scanning for security issues.')