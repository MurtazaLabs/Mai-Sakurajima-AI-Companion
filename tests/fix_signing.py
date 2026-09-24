with open('E:\\Mai_ai\\plugins\\signing.py', 'rb') as f:
    content = f.read()

# Find the duplicate pattern
idx = content.find(b'return False, f"Verification failed: {e}", None')
if idx >= 0:
    idx2 = content.find(b'return False, f"Verification failed: {e}", None', idx + 1)
    if idx2 >= 0:
        print(f'Found duplicate at byte {idx2}')
        # Remove the duplicate
        fixed = content[:idx2] + content[idx2+45:]
        with open('E:\\Mai_ai\\plugins\\signing.py', 'wb') as f:
            f.write(fixed)
        print('Fixed!')
    else:
        print('No duplicate found')