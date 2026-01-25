try:
    import google.generativeai as genai
    print("SUCCESS: google-generativeai imported successfully.")
    print(f"Location: {genai.__file__}")
except ImportError as e:
    print(f"ERROR: Failed to import google-generativeai: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")

import sys
print(f"Python Executable: {sys.executable}")
print(f"Python Check: {sys.version}")
