import os
import logging
import time
import click
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pymilvus import connections, utility
from watchdog.observers import Observer

# Load Env (MUST be before blueprint imports)
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
load_dotenv(dotenv_path)

# Also load .env.local if it exists (for overrides)
dotenv_local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env.local')
if os.path.exists(dotenv_local_path):
    load_dotenv(dotenv_local_path, override=True)
    logging.info(f"Loaded config from {dotenv_local_path}")

# Import Blueprints
from features.common.routes import common_bp
from features.knowledge.routes import knowledge_bp
from features.canvas.routes import canvas_bp
from features.canvas.converter_routes import canvas_converter_bp  # Phase 5: DOCX互转
from features.smart_canvas.routes import smart_canvas_bp
from features.analysis.routes import analysis_bp
from features.audit.routes import audit_bp
from features.smart_filler.routes import smart_filler_bp
from features.advisor.routes import advisor_bp
from features.agent_anything.routes import agent_anything_bp # AnythingLLM Agent
from features.file_search.routes import file_search_bp  # 智能文件搜索
from features.remote_control.routes import remote_control_bp  # OpenClaw Remote Control

# ⚠️ 知识库CLI命令（独立文件，请勿随意修改）
from features.knowledge.cli import register_knowledge_commands

# Import Services for CLI (用于 flask ingest 命令)
from features.knowledge.services import (
    ingest_all_data,
    MILVUS_HOST, MILVUS_PORT
)

# 重新初始化知识库路径（在load_dotenv之后）
from features.knowledge import services as knowledge_services
knowledge_services.KNOWLEDGE_BASE_DIR = knowledge_services.get_knowledge_base_dir()
knowledge_services.KNOWLEDGE_BASE_DIR_NOMIC = knowledge_services.get_knowledge_base_dir_nomic()
logging.info(f"Knowledge base directories: {knowledge_services.KNOWLEDGE_BASE_DIR}, {knowledge_services.KNOWLEDGE_BASE_DIR_NOMIC}")

# Configure Logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("backend_debug.log", encoding='utf-8'),
                        logging.StreamHandler()
                    ])

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register Blueprints
    app.register_blueprint(common_bp, url_prefix='/api')
    app.register_blueprint(knowledge_bp, url_prefix='/api') # /list-collections, /find-related
    app.register_blueprint(canvas_bp, url_prefix='/api/canvas') # /upload, /chat, /preview...
    app.register_blueprint(canvas_converter_bp)  # Phase 5: /api/canvas/export-to-docx, /import-from-docx
    app.register_blueprint(smart_canvas_bp, url_prefix='/api/smart_canvas') # /upload (mammoth)
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis') 
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(smart_filler_bp, url_prefix='/api/smart-filler')
    app.register_blueprint(advisor_bp, url_prefix='/api/advisor') # /suggestions - Fixed from /api/agent
    app.register_blueprint(agent_anything_bp, url_prefix='/api/agent-anything') # /audit
    app.register_blueprint(file_search_bp, url_prefix='/api/file-search') # 智能文件搜索
    app.register_blueprint(remote_control_bp, url_prefix='/api/remote-control')  # OpenClaw Remote Control

    # Initialize Milvus Connection (Disabled for manual connection preference)
    # try:
    #     connections.connect("default", host=os.getenv("MILVUS_HOST", "127.0.0.1"), port=os.getenv("MILVUS_PORT", "19530"))
    #     logging.info("Connected to Milvus.")
    # except Exception as e:
    #     logging.error(f"Failed to connect to Milvus on startup: {e}")

    return app

app = create_app()

# ⚠️ 注册知识库CLI命令（定义在 features/knowledge/cli.py）
register_knowledge_commands(app)

# --- CLI Commands ---

@app.cli.command("ingest")
def ingest_command():
    """Ingest documents from knowledge_base directory into Milvus."""
    ingest_all_data()
    click.echo("Ingestion complete.")


# ⚠️ watch 和 watch-nomic 命令已移至 features/knowledge/cli.py

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5179"))
    
    # Use standard Flask dev server (WSGI)
    print("Starting Flask Server...")
    logging.info("--- Deployment Version Check: v2026.02.08-Debug-ForcePush ---")
    app.run(host=host, port=port, debug=True)
