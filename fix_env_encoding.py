import os

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', '.env')

# Try reading with GBK (common for Chinese Windows) or ANSI
try:
    with open(env_path, 'r', encoding='gbk') as f:
        content = f.read()
    print("Successfully read with GBK.")
except UnicodeDecodeError:
    try:
        with open(env_path, 'r', encoding='mbcs') as f: # Try system default
            content = f.read()
        print("Successfully read with MBCS.")
    except Exception as e:
        print(f"Failed to read file: {e}")
        exit(1)

# Write back as UTF-8
with open(env_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Successfully converted {env_path} to UTF-8.")
