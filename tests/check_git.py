import subprocess

result = subprocess.run(['git', '-C', r'E:\Mai_ai', 'rev-parse', '--show-toplevel'], 
                       capture_output=True, text=True, cwd=r'E:\Mai_ai')
print(f'Git root: "{result.stdout.strip()}"')
print(f'Return code: {result.returncode}')
print(f'Stderr: {result.stderr}')