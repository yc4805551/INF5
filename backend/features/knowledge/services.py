import os
import logging
import requests
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymilvus import connections, Collection, utility, FieldSchema, DataType, CollectionSchema
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Constants
MILVUS_HOST = os.getenv("MILVUS_HOST", "127.0.0.1")
if MILVUS_HOST.startswith("http://"): MILVUS_HOST = MILVUS_HOST.replace("http://", "")
elif MILVUS_HOST.startswith("https://"): MILVUS_HOST = MILVUS_HOST.replace("https://", "")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1")
if "0.0.0.0" in OLLAMA_HOST: OLLAMA_HOST = OLLAMA_HOST.replace("0.0.0.0", "127.0.0.1")
if not OLLAMA_HOST.startswith("http"): OLLAMA_HOST = f"http://{OLLAMA_HOST}"
OLLAMA_PORT = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_EMBED_API_URL = f"{OLLAMA_HOST}:{OLLAMA_PORT}/api/embeddings"

DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
MODEL_MAPPING = {
    "kb_qwen": "qwen3-embedding:0.6b",
    "kb_nomic": "nomic-embed-text"
}

KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
KNOWLEDGE_BASE_DIR_NOMIC = os.getenv("KNOWLEDGE_BASE_DIR_NOMIC", "./knowledge_base_nomic")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
INGEST_WORKERS = int(os.getenv("INGEST_WORKERS", 8))

def get_model_for_collection(collection_name: str) -> str:
    for key, model_name in MODEL_MAPPING.items():
        if key in collection_name:
            return model_name
    return DEFAULT_EMBEDDING_MODEL

def get_ollama_embedding(text: str, model_name: str):
    try:
        payload = {"model": model_name, "prompt": text}
        response = requests.post(OLLAMA_EMBED_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        if "embedding" not in response_data:
            raise ValueError(f"Ollama API missing 'embedding'")
        return response_data["embedding"]
    except Exception as e:
        logging.error(f"Ollama embedding error: {e}")
        raise

def create_milvus_collection(collection_name, dim):
    if utility.has_collection(collection_name):
        return Collection(collection_name)
    logging.info(f"Creating collection '{collection_name}' (dim: {dim})...")
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source_file", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="full_path", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
    ]
    schema = CollectionSchema(fields, description=f"KB Collection: {collection_name}")
    collection = Collection(name=collection_name, schema=schema)
    index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
    collection.create_index(field_name="embedding", index_params=index_params)
    return collection

def text_to_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not text: return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"Hash error: {e}")
        return None

def upsert_file_to_milvus(file_path: str, collection_name: str, model_name: str):
    filename = os.path.basename(file_path)
    try:
        current_hash = get_file_hash(file_path)
        if not os.path.exists(file_path): return
        
        with open(file_path, 'r', encoding='utf-8') as f: 
            content = f.read()
        if not content.strip(): return
            
        collection = Collection(collection_name)
        collection.load()
        
        # Deduplication check
        try:
            expr = f"source_file == '{filename}'"
            result = collection.query(expr, output_fields=["text"])
            if len(result) > 0 and current_hash:
                first_chunk = result[0].get("text", "")
                if content.startswith(first_chunk) and len(content) > 0:
                    logging.info(f"File '{filename}' unchanged, skipping.")
                    return
        except Exception as e:
            logging.warning(f"Existence check failed: {e}")
            
        # Delete old
        collection.delete(f"source_file == '{filename}'")
        
        chunks = text_to_chunks(content)
        if not chunks: return
        
        entities_to_insert = []
        logging.info(f"Processing {len(chunks)} chunks for '{filename}'...")
        with ThreadPoolExecutor(max_workers=INGEST_WORKERS) as executor:
            future_to_chunk = {executor.submit(get_ollama_embedding, chunk, model_name): (i, chunk) for i, chunk in enumerate(chunks)}
            for future in as_completed(future_to_chunk):
                try:
                    embedding = future.result()
                    i, chunk = future_to_chunk[future]
                    entity = {
                        "id": str(uuid.uuid4()),
                        "text": chunk,
                        "source_file": filename,
                        "chunk_index": i,
                        "full_path": file_path,
                        "embedding": embedding
                    }
                    entities_to_insert.append(entity)
                except Exception as e:
                    logging.error(f"Embedding failed: {e}")
        if entities_to_insert:
            collection.insert(entities_to_insert)
            collection.flush()
            logging.info(f"Upserted file: {filename}")
    except Exception as e:
        logging.error(f"Failed to upsert '{filename}': {e}")
    finally:
        if 'collection' in locals(): collection.release()

def process_file_delete(file_path, collection_name):
    filename = os.path.basename(file_path)
    try:
        collection = Collection(collection_name)
        collection.load()
        collection.delete(f"source_file == '{filename}'")
        logging.info(f"Deleted index for: {filename}")
    except Exception as e:
        logging.error(f"Delete failed: {e}")
    finally:
        if 'collection' in locals(): collection.release()

class KnowledgeBaseEventHandler(FileSystemEventHandler):
    def __init__(self, collection_to_watch, model_name, base_dir=None):
        self.collection_to_watch = collection_to_watch
        self.model_name = model_name
        self.base_dir = base_dir or KNOWLEDGE_BASE_DIR
        self.watch_path = os.path.normpath(os.path.join(self.base_dir, self.collection_to_watch))
        logging.info(f"Watcher initialized for: {self.watch_path}")
    def process_if_relevant(self, event):
        if event.is_directory: return
        if not (event.src_path.endswith(".txt") or event.src_path.endswith(".md")): return
        event_dir = os.path.normpath(os.path.dirname(event.src_path))
        if event_dir.lower() != self.watch_path.lower(): return
        logging.info(f"Event {event.event_type}: {event.src_path}")
        if event.event_type in ('created', 'modified'):
            upsert_file_to_milvus(event.src_path, self.collection_to_watch, self.model_name)
        elif event.event_type == 'deleted':
            process_file_delete(event.src_path, self.collection_to_watch)
        elif event.event_type == 'moved':
            process_file_delete(event.src_path, self.collection_to_watch)
            dest_dir = os.path.normpath(os.path.dirname(event.dest_path))
            if dest_dir.lower() == self.watch_path.lower():
                upsert_file_to_milvus(event.dest_path, self.collection_to_watch, self.model_name)
    def on_created(self, event): self.process_if_relevant(event)
    def on_modified(self, event): self.process_if_relevant(event)
    def on_deleted(self, event): self.process_if_relevant(event)
    def on_moved(self, event): self.process_if_relevant(event)

def ingest_all_data():
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logging.error(f"KB Dir '{KNOWLEDGE_BASE_DIR}' not found.")
        return
    for collection_name in os.listdir(KNOWLEDGE_BASE_DIR):
        collection_path = os.path.join(KNOWLEDGE_BASE_DIR, collection_name)
        if not os.path.isdir(collection_path): continue
        logging.info(f"--- Processing Collection: {collection_name} ---")
        model_to_use = get_model_for_collection(collection_name)
        try:
            dummy_embedding = get_ollama_embedding("test", model_to_use)
            dim = len(dummy_embedding)
        except Exception as e:
            logging.error(f"Cannot get model dimension: {e}")
            continue
        create_milvus_collection(collection_name, dim)
        for filename in os.listdir(collection_path):
            file_path = os.path.join(collection_path, filename)
            if not (filename.endswith(".txt") or filename.endswith(".md")): continue
            upsert_file_to_milvus(file_path, collection_name, model_to_use)
