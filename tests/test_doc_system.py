import json
import os
import sys

import pytest

sys.path.insert(0, r'E:\Mai_ai')

def test_documentation():
    from pathlib import Path

    config_path = Path(r'C:\Users\Administrator\.config\opencode\documentation.json')
    project_path = Path(r'E:\Mai_ai')
    vault_path = Path(r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault')
    if not config_path.is_file() or not project_path.is_dir() or not vault_path.is_dir():
        pytest.skip('Requires the developer-local OpenCode/Obsidian environment')
    
    # Load config
    with open(r'C:\Users\Administrator\.config\opencode\documentation.json', 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
    
    vault_path = Path(config["OBSIDIAN_VAULT_PATH"])
    print(f"Vault path: {config['OBSIDIAN_VAULT_PATH']}")
    print(f"Vault exists: {Path(config['OBSIDIAN_VAULT_PATH']).exists()}")
    
    # Check if vault exists
    vault_path = Path(config["OBSIDIAN_VAULT_PATH"])
    if not vault_path.exists():
        print("ERROR: Vault path does not exist!")
        return
    
    # Check project detection
    # Test git root detection
    import subprocess
    from pathlib import Path
    result = subprocess.run(['git', '-C', r'E:\Mai_ai', 'rev-parse', '--show-toplevel'], 
                          capture_output=True, text=True, cwd=r'E:\Mai_ai')
    print(f"Git root: {result.stdout.strip()}")
    
    # Check vault structure
    vault = Path(r'C:\Users\Administrator\Documents\OpenCode Obsidian Vault')
    print(f"Vault exists: {vault.exists()}")
    
    for root, dirs, files in os.walk(vault):
        for d in dirs:
            print(f"  Dir: {os.path.relpath(os.path.join(root, d), vault)}")
        for f in files:
            print(f"  File: {os.path.relpath(os.path.join(root, f), vault)}")

if __name__ == "__main__":
    test_documentation()