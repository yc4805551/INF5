"""
知识库监控CLI命令
=====================================
⚠️ 警告：此文件包含知识库文件监控的核心功能
请勿随意修改，除非明确需要调整知识库监控逻辑

功能说明：
- flask watch: 监控 kb_qwen_0_6b 知识库文件变化
- flask watch-nomic: 监控 kb_nomic 知识库文件变化
- 自动将新增/修改的文件导入到 Milvus 向量数据库
- 使用 PollingObserver 确保 Windows 兼容性

依赖服务：
- Milvus (向量数据库)
- Ollama (嵌入模型)
"""

import os
import time
import platform
import click
from pymilvus import connections, utility
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from .services import (
    KnowledgeBaseEventHandler,
    get_model_for_collection,
    MILVUS_HOST,
    MILVUS_PORT
)


def register_knowledge_commands(app):
    """
    注册知识库相关的 Flask CLI 命令
    
    Args:
        app: Flask application instance
    """
    
    @app.cli.command("watch")
    def watch_command():
        """
        监控 kb_qwen_0_6b 知识库目录的文件变化
        
        当目录中的 .txt 或 .md 文件发生变化时：
        - 新增/修改：自动导入到 Milvus
        - 删除：从 Milvus 中移除对应记录
        
        环境变量：
            KNOWLEDGE_BASE_DIR: 知识库根目录路径
        
        示例：
            flask watch
        """
        collection_to_watch = 'kb_qwen_0_6b'
        
        # 动态获取知识库路径（确保读取最新的环境变量）
        kb_dir = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
        # 实际监控的是子目录
        watch_path = os.path.join(kb_dir, collection_to_watch)
        
        click.echo("=" * 60)
        click.echo("📚 知识库文件监控 - Qwen 模型")
        click.echo("=" * 60)
        click.echo(f"📂 知识库根目录: {kb_dir}")
        click.echo(f"👁️  监控路径: {watch_path}")
        
        # 检查目录是否存在
        if not os.path.exists(watch_path):
            click.echo(f"❌ 错误: 目录 '{watch_path}' 不存在！")
            click.echo(f"   请创建该目录或检查 KNOWLEDGE_BASE_DIR 配置")
            return
        
        # 连接 Milvus
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            click.echo(f"✅ 已连接到 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
        except Exception as e:
            click.echo(f"❌ Milvus 连接失败: {e}")
            return

        # 检查集合是否存在
        model_name = get_model_for_collection(collection_to_watch)
        if not utility.has_collection(collection_to_watch):
            click.echo(f"❌ 错误: 集合 '{collection_to_watch}' 不存在")
            click.echo(f"   请先运行: flask ingest")
            return

        # 创建事件处理器
        event_handler = KnowledgeBaseEventHandler(collection_to_watch, model_name, base_dir=kb_dir)
        
        # Windows 上使用 PollingObserver 更可靠
        if platform.system() == 'Windows':
            observer = PollingObserver()
            click.echo("🔍 使用 PollingObserver (Windows 兼容模式)")
        else:
            observer = Observer()
            click.echo("🔍 使用 默认 Observer")
        
        observer.schedule(event_handler, watch_path, recursive=False)
        click.echo("=" * 60)
        click.echo(f"✅ 监控已启动: {collection_to_watch}")
        click.echo(f"   等待文件变化... (按 Ctrl+C 停止)")
        click.echo("=" * 60)
        
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n⏹️  停止监控...")
            observer.stop()
        observer.join()
        click.echo("✅ 监控已停止")

    @app.cli.command("watch-nomic")
    def watch_nomic_command():
        """
        监控 kb_nomic 知识库目录的文件变化
        
        当目录中的 .txt 或 .md 文件发生变化时：
        - 新增/修改：自动导入到 Milvus
        - 删除：从 Milvus 中移除对应记录
        
        环境变量：
            KNOWLEDGE_BASE_DIR_NOMIC: Nomic 知识库根目录路径
        
        示例：
            flask watch-nomic
        """
        collection_to_watch = 'kb_nomic'
        
        # 动态获取知识库路径
        kb_dir_nomic = os.getenv("KNOWLEDGE_BASE_DIR_NOMIC", "./knowledge_base_nomic")
        watch_path = os.path.join(kb_dir_nomic, collection_to_watch)
        
        click.echo("=" * 60)
        click.echo("📚 知识库文件监控 - Nomic 模型")
        click.echo("=" * 60)
        click.echo(f"📂 知识库根目录: {kb_dir_nomic}")
        click.echo(f"👁️  监控路径: {watch_path}")
        
        # 检查目录是否存在
        if not os.path.exists(watch_path):
            click.echo(f"❌ 错误: 目录 '{watch_path}' 不存在！")
            click.echo(f"   请创建该目录或检查 KNOWLEDGE_BASE_DIR_NOMIC 配置")
            return
        
        # 连接 Milvus
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            click.echo(f"✅ 已连接到 Milvus: {MILVUS_HOST}:{MILVUS_PORT}")
        except Exception as e:
            click.echo(f"❌ Milvus 连接失败: {e}")
            return
            
        # 检查集合是否存在
        model_name = get_model_for_collection(collection_to_watch)
        if not utility.has_collection(collection_to_watch):
            click.echo(f"❌ 错误: 集合 '{collection_to_watch}' 不存在")
            click.echo(f"   请先运行: flask ingest")
            return

        # 创建事件处理器
        event_handler = KnowledgeBaseEventHandler(collection_to_watch, model_name, base_dir=kb_dir_nomic)
        
        # Windows 上使用 PollingObserver
        if platform.system() == 'Windows':
            observer = PollingObserver()
            click.echo("🔍 使用 PollingObserver (Windows 兼容模式)")
        else:
            observer = Observer()
            click.echo("🔍 使用 默认 Observer")
        
        observer.schedule(event_handler, watch_path, recursive=False)
        click.echo("=" * 60)
        click.echo(f"✅ 监控已启动: {collection_to_watch}")
        click.echo(f"   等待文件变化... (按 Ctrl+C 停止)")
        click.echo("=" * 60)
        
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\n⏹️  停止监控...")
            observer.stop()
        observer.join()
        click.echo("✅ 监控已停止")
