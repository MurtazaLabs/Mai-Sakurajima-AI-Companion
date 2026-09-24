import sys, os
sys.path.insert(0, r'C:\Users\Administrator\.config\opencode\plugins')

try:
    import opencode_project_documentation
    print('Plugin loaded successfully')
except Exception as e:
    print(f'Import failed: {e}')