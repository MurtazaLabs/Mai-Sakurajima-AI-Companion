import json
from pathlib import Path

with open(r'C:\Users\Administrator\.config\opencode\documentation.json', 'r') as f:
    config = json.load(f)
print('Config loaded:', json.dumps(config, indent=2))

# Test the vault path
vault = Path(config["OBSIDIAN_VAULT_PATH"])
print(f'Vault exists: {vault.exists()}')
print(f'Vault path: {vault}')
print(f'Vault expanded: {vault.expanduser()}')