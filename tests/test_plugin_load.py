import sys

sys.path.insert(0, r'C:\Users\Administrator\.config\opencode\plugins')

try:
    print('Plugin loaded successfully')
except Exception as e:
    print(f'Import failed: {e}')