import os
import logging
import time
import click
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pymilvus import connections, utility
from watchdog.observers import Observer

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

# Import Services for CLI
from features.knowledge.services import (
    ingest_all_data, 
    KnowledgeBaseEventHandler, 
    get_model_for_collection,
    KNOWLEDGE_BASE_DIR, KNOWLEDGE_BASE_DIR_NOMIC,
    MILVUS_HOST, MILVUS_PORT
)

# Load Env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env')
load_dotenv(dotenv_path)

# Also load .env.local if it exists (for overrides)
dotenv_local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', '.env.local')
if os.path.exists(dotenv_local_path):
    load_dotenv(dotenv_local_path, override=True)
    logging.info(f"Loaded config from {dotenv_local_path}")

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

    # Initialize Milvus Connection
    try:
        connections.connect("default", host=os.getenv("MILVUS_HOST", "127.00.1"), port=os.getenv("MILVUS_PORT", "19530"))
        logging.info("Connected to Milvus.")
    except Exception as e:
        logging.error(f"Failed to connect to Milvus on startup: {e}")

    return app

app = create_app()

# --- CLI Commands ---

@app.cli.command("ingest")
def ingest_command():
    """Ingest documents from knowledge_base directory into Milvus."""
    ingest_all_data()
    click.echo("Ingestion complete.")

@app.cli.command("watch")
def watch_command():
    """Watch knowledge_base directory for changes."""
    collection_to_watch = 'kb_qwen_0_6b'
    
    # 动态获取知识库路径（确保读取最新的环境变量）
    kb_dir = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
    # 实际监控的是子目录
    watch_path = os.path.join(kb_dir, collection_to_watch)
    
    click.echo(f"📂 Knowledge base dir: {kb_dir}")
    click.echo(f"👁️  Actual watch path: {watch_path}")
    
    # 检查目录是否存在
    if not os.path.exists(watch_path):
        click.echo(f"❌ Error: Directory '{watch_path}' does not exist!")
        click.echo(f"   Please create it or check your KNOWLEDGE_BASE_DIR setting.")
        return
    
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception as e:
        click.echo(f"Error connecting to Milvus: {e}")
        return

    model_name = get_model_for_collection(collection_to_watch)
    if not utility.has_collection(collection_to_watch):
        click.echo(f"Error: Collection '{collection_to_watch}' does not exist. Run 'flask ingest' first.")
        return

    event_handler = KnowledgeBaseEventHandler(collection_to_watch, model_name, base_dir=kb_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_path, recursive=False)  # 不递归，只监控此目录
    click.echo(f"✅ Watching: {collection_to_watch} ({watch_path})")
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

@app.cli.command("watch-nomic")
def watch_nomic_command():
    """Watch knowledge_base_nomic directory for changes."""
    collection_to_watch = 'kb_nomic'
    
    # 动态获取知识库路径（确保读取最新的环境变量）
    kb_dir_nomic = os.getenv("KNOWLEDGE_BASE_DIR_NOMIC", "./knowledge_base_nomic")
    
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception as e:
        click.echo(f"Error connecting to Milvus: {e}")
        return
        
    model_name = get_model_for_collection(collection_to_watch)
    if not utility.has_collection(collection_to_watch):
        click.echo(f"Error: Collection '{collection_to_watch}' does not exist.")
        return

    event_handler = KnowledgeBaseEventHandler(collection_to_watch, model_name, base_dir=kb_dir_nomic)
    observer = Observer()
    # Ensure dir exists or observer might fail?
    if not os.path.exists(kb_dir_nomic):
         click.echo(f"Warning: Directory '{kb_dir_nomic}' does not exist.")
    
    observer.schedule(event_handler, kb_dir_nomic, recursive=True)
    click.echo(f"✅ Watching: {collection_to_watch} ({kb_dir_nomic})")
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5179"))
    
    # Use standard Flask dev server (WSGI)
    print("Starting Flask Server...")
    app.run(host=host, port=port, debug=True)
