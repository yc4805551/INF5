import requests
import os
import sys

# Configuration from your environment or defaults
host = os.getenv("OLLAMA_HOST", "0.0.0.0")
port = os.getenv("OLLAMA_PORT", "11434")

# Logic from app.py
if "0.0.0.0" in host:
    print(f"Detected 0.0.0.0 in host, changing to 127.0.0.1")
    host = host.replace("0.0.0.0", "127.0.0.1")

if not host.startswith("http"):
    host = f"http://{host}"

url = f"{host}:{port}/api/tags" # Simple endpoint to list models

print(f"--- Ollama Connection Diagnostic ---")
print(f"Target URL: {url}")
print(f"Environment OLLAMA_HOST: {os.getenv('OLLAMA_HOST')}")
print(f"Environment HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
print(f"Environment HTTPS_PROXY: {os.getenv('HTTPS_PROXY')}")
print(f"Environment NO_PROXY: {os.getenv('NO_PROXY')}")
print(f"----------------------------------")

try:
    print("Attempting connection...")
    response = requests.get(url, timeout=5)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("SUCCESS: Connected to Ollama!")
        print("Available Models:", [m['name'] for m in response.json().get('models', [])])
    else:
        print(f"FAILURE: Connected but received error status: {response.text}")
except Exception as e:
    print(f"CRITICAL FAILURE: Could not connect.")
    print(f"Error Details: {e}")
    print("\nTroubleshooting Tips:")
    print("1. If you see 'ProxyError', disable your VPN or set NO_PROXY=127.0.0.1")
    print("2. If you see 'ConnectionRefused', Ollama is not running or not on port 11434.")
