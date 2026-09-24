import sys, os
sys.path.insert(0, r'E:\Mai_ai')

import os
import subprocess

# Test git root detection
result = subprocess.run(['git', '-C', r'E:\Mai_ai', 'rev-parse', '--show-toplevel'], 
                       capture_output=True, text=True, cwd=r'E:\Mai_ai')
print(f"Git root: {result.stdout.strip()}")

# Check vault structure
vault = r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault'
print(f"Vault exists: {os.path.exists(vault)}")

for root, dirs, files in os.walk(vault):
    for d in dirs:
        print(f"  Dir: {os.path.relpath(os.path.join(root, d), vault)}")
    for f in files:
        print(f"  File: {os.path.relpath(os.path.join(root, f), vault)}")