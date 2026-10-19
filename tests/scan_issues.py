import os
import re
import sys

sys.path.insert(0, r'E:\Mai_ai')

print('=== SCANNING FOR COMMON ISSUES ===')

issues = []

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
                    
                    # Check for print statements (should use logging)
                    if re.match(r'^\s*print\(', line) and 'test' not in path.lower() and 'example' not in path.lower():
                        issues.append(f'{rel}:{i}: Print statement (should use logging)')
                    
                    # Check for hardcoded Windows paths
                    if re.search(r'[CDE]:\\\\', line) and 'test' not in path.lower() and 'example' not in path.lower():
                        issues.append(f'{rel}:{i}: Hardcoded Windows path')
                    
                    # Check for hardcoded credentials
                    if re.search(r'(password|secret|key|token)\s*=\s*[\'"][^\'"]+[\'"]', line, re.IGNORECASE) and 'test' not in path.lower() and 'example' not in path.lower():
                        issues.append(f'{rel}:{i}: Possible hardcoded credential')
                    
                    # Check for TODO/FIXME comments
                    if 'TODO' in line or 'FIXME' in line:
                        issues.append(f'{rel}:{i}: TODO/FIXME: {line.strip()[:80]}')
                        
                    # Check for bare except (already checked - none found)
                    
            except:
                pass

# Print summary
print('=== ISSUE SCAN SUMMARY ===')
for issue in issues[:50]:
    print(f'  {issue}')
print(f'\nTotal issues found: {len(issues)}')
if len(issues) > 50:
    print(f'  (showing first 50 of {len(issues)})')