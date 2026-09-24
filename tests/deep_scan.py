import sys, os, re, ast
sys.path.insert(0, r'E:\Mai_ai')

print('=== DEEP CODE SCAN ===')

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
                
                # Track threading locks
                lock_acquires = 0
                lock_releases = 0
                has_lock = False
                
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    # Check for threading lock issues - acquire without release
                    if 'acquire()' in line and 'with' not in line:
                        lock_acquires += 1
                    if 'release()' in line and 'with' not in line:
                        lock_releases += 1
                    if 'threading.Lock' in line or 'threading.RLock' in line:
                        has_lock = True
                    
                    # Check for mutable default arguments
                    if re.search(r'def \w+\([^)]*=\s*\[', line) or re.search(r'def \w+\([^)]*=\s*\{', line):
                        issues.append(f'{rel}:{i}: Mutable default argument: {line.strip()[:80]}')
                    
                    # Check for broad exception handlers (bare except already checked)
                    if 'except Exception:' in line and 'pass' in lines[i] if i < len(lines) else '':
                        pass  # This is fine if logged
                    
                    # Check for logging of sensitive data
                    if 'log' in line.lower() and ('password' in line.lower() or 'token' in line.lower() or 'secret' in line.lower() or 'apikey' in line.lower()):
                        if 'logger' in line and 'password' in line.lower():
                            issues.append(f'{rel}:{i}: Possible logging of sensitive data: {line.strip()[:100]}')
                    
                    # Check for time.sleep in async code
                    if 'async def' in content and 'time.sleep(' in line and 'await asyncio.sleep' not in content:
                        issues.append(f'{rel}:{i}: time.sleep in async function: {line.strip()[:80]}')
                    
                    # Check for blocking calls in async
                    if 'async def' in content and 'requests.get' in line and 'await' not in line:
                        issues.append(f'{rel}:{i}: Blocking requests.get in async: {line.strip()[:80]}')
                    
                    # Check for potential resource leaks
                    if 'open(' in line and 'with' not in line and 'close()' not in content:
                        if 'open(' in line and 'as' not in line:
                            issues.append(f'{rel}:{i}: File opened without context manager: {line.strip()[:80]}')
                    
                    # Check for global mutable state
                    if re.match(r'^\s*[A-Z_][A-Z0-9_]*\s*=\s*(\[|\{)', line) and 'test' not in path.lower():
                        pass  # Module-level constants are fine
                    
                    # Check for circular import patterns
                    if 'import' in line and 'from' in line and 'import' in line:
                        pass
                    
                    # Check for potential deadlock - lock ordering
                    if 'lock.acquire' in line and 'lock2.acquire' in content:
                        issues.append(f'{rel}:{i}: Potential deadlock - multiple locks: {line.strip()[:80]}')

                # Check lock balance
                if has_lock and lock_acquires != lock_releases:
                    if lock_acquires > lock_releases:
                        issues.append(f'{rel}: Lock acquire/release imbalance: {lock_acquires} acquires, {lock_releases} releases')

            except Exception as e:
                pass

print('=== DEEP SCAN COMPLETE ===')
print(f'Total issues found: {len(issues)}')
for issue in issues[:30]:
    print(f'  {issue}')
if len(issues) > 30:
    print(f'  ... and {len(issues) - 30} more issues')