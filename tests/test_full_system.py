import os
import subprocess
import sys

sys.path.insert(0, r'E:\Mai_ai')

def test_documentation():
    # Test the documentation system
    from pathlib import Path
    
    # Test 1: Check if vault exists and has correct structure
    vault = Path(r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault')
    print(f"Vault exists: {vault.exists()}")
    
    # Check if Projects directory exists
    projects_dir = Path(r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault\Projects')
    print(f"Projects dir exists: {projects_dir.exists()}")
    
    # Check if there are any projects
    if projects_dir.exists():
        projects = list(projects_dir.iterdir())
        print(f"Projects: {[p.name for p in projects]}")
    else:
        print("No Projects directory found")
    
    # Test git root detection
    result = subprocess.run(['git', '-C', r'E:\Mai_ai', 'rev-parse', '--show-toplevel'], 
                          capture_output=True, text=True, cwd=r'E:\Mai_ai')
    print(f"Git root: '{result.stdout.strip()}'")
    
    # Check vault structure
    vault = Path(r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault')
    print("\nVault structure:")
    for root, dirs, files in os.walk(vault):
        for d in dirs:
            rel = os.path.relpath(os.path.join(root, d), vault)
            print(f"  Dir: {rel}")
        for f in files:
            print(f"  File: {os.path.relpath(os.path.join(root, f), vault)}")

if __name__ == "__main__":
    test_documentation()