
print("--- TEST 1: Reproduction ---")
s = "经审核"
try:
    print(f"Original: {s}")
    garbled = s.encode('utf-8').decode('unicode_escape')
    print(f"Garbled: {garbled}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- TEST 2: Safe Unescape ---")
input_str = r"经审核\n同意"
# Need to turn \\n into \n but keep 经审核 intact.
print(f"Input: {input_str}")

# Attempt 1: Manual replacement
safe = input_str.replace(r"\n", "\n")
print(f"Manual Replace: {safe}")

# Attempt 2: ast.literal_eval
import ast
try:
    # We must wrap in quotes to make it a string literal
    # But if input has quotes, we must be careful.
    # formatting as f"'{input_str}'" might break if input_str has single quotes.
    quoted = f'"{input_str}"' 
    decoded = ast.literal_eval(quoted)
    print(f"AST Eval: {decoded}")
except Exception as e:
    print(f"AST Eval Failed: {e}")
