import os
from dotenv import load_dotenv

# Load .env
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', '.env')
load_dotenv(dotenv_path)

kb_dir = os.getenv("KNOWLEDGE_BASE_DIR")
kb_nomic_dir = os.getenv("KNOWLEDGE_BASE_DIR_NOMIC")

print(f"KNOWLEDGE_BASE_DIR: {kb_dir}")
print(f"KNOWLEDGE_BASE_DIR_NOMIC: {kb_nomic_dir}")
