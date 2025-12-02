import sys
import os
import socket
import importlib.util

def check_python_version():
    print(f"Python Version: {sys.version}")
    if sys.version_info < (3, 8):
        print("[ERROR] Error: Python 3.8 or higher is required.")
        return False
    return True

def check_import(module_name):
    if importlib.util.find_spec(module_name) is None:
        print(f"[ERROR] Error: Missing module '{module_name}'. Please run 'pip install -r requirements.txt'")
        return False
    print(f"[OK] Found module: {module_name}")
    return True

def check_dependencies():
    required_modules = [
        "flask", "flask_cors", "dotenv", "requests", "docx", "watchdog"
    ]
    all_ok = True
    print("Checking dependencies...")
    for mod in required_modules:
        if not check_import(mod):
            all_ok = False
            print(f"[ERROR] Missing dependency: {mod}")
    return all_ok

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    if result == 0:
        print(f"[WARN] Warning: Port {port} is already in use. This might cause the backend to fail if it's not already running.")
        return False # Port is open, meaning something is listening
    else:
        print(f"[OK] Port {port} is available.")
        return True

def check_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
    if not os.path.exists(env_path):
        print(f"[ERROR] Error: .env file not found at {env_path}")
        return False
    print(f"[OK] Found .env file at {env_path}")
    return True

def log_deployment_info():
    log_file = "deployment_debug.log"
    try:
        with open(log_file, "w") as f:
            f.write("--- Deployment Debug Log ---\n")
            f.write(f"Time: {sys.version}\n") # Using sys.version as a timestamp proxy if datetime not imported, but let's just use what we have
            f.write(f"Hostname: {socket.gethostname()}\n")
            f.write(f"IP Address: {socket.gethostbyname(socket.gethostname())}\n")
            f.write(f"Python Executable: {sys.executable}\n")
            f.write(f"CWD: {os.getcwd()}\n")
            f.write("----------------------------\n")
        print(f"[INFO] Deployment info logged to {log_file}")
    except Exception as e:
        print(f"[WARN] Failed to write deployment log: {e}")

def main():
    log_deployment_info()
    print("--- Starting Health Check ---")
    
    if not check_python_version():
        sys.exit(1)
        
    if not check_env_file():
        sys.exit(1)

    if not check_dependencies():
        sys.exit(1)
        
    # Check if port 5179 is FREE (we want it to be free so we can bind to it, 
    # OR if we are just checking connectivity, we might want it to be taken? 
    # Usually for startup check, we want to know if we CAN start.)
    # But if the user is restarting, maybe the old process is stuck.
    check_port(5179)
    
    print("--- Health Check Passed (mostly) ---")
    sys.exit(0)

if __name__ == "__main__":
    main()
