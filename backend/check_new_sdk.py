try:
    from google import genai
    print("SUCCESS: google.genai imported successfully.")
    print(f"Location: {genai.__file__}")
except ImportError as e:
    print(f"ERROR: Failed to import google.genai: {e}")
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")

import sys
print(f"Python Executable: {sys.executable}")
