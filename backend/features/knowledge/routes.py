from flask import Blueprint, request, jsonify
from pymilvus import connections, utility, Collection
import logging
import os
from .services import (
    MILVUS_HOST, MILVUS_PORT, 
    get_model_for_collection, get_ollama_embedding
)

knowledge_bp = Blueprint('knowledge', __name__)

@knowledge_bp.route('/list-collections', methods=['GET'])
def list_collections():
    try:
        try:
            collections = utility.list_collections()
        except Exception:
            logging.warning("Retrying Milvus connection...")
            try:
                connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
                collections = utility.list_collections()
            except Exception as e:
                logging.error(f"Milvus connection failed: {e}")
                return jsonify({"collections": [], "error": "Milvus unavailable"})
        return jsonify({"collections": collections})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@knowledge_bp.route('/find-related', methods=['POST'])
def find_related():
    try:
        data = request.get_json()
        query_text = data.get('text')
        collection_name = data.get('collection_name')
        top_k = data.get('top_k', 10)
        
        if not query_text or not collection_name:
            return jsonify({"error": "Missing text or collection_name"}), 400
        
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        except Exception as e:
            return jsonify({"error": f"Milvus connection error: {str(e)}"}), 500

        if not utility.has_collection(collection_name):
            return jsonify({"error": f"Collection '{collection_name}' not found"}), 404

        model_to_use = get_model_for_collection(collection_name)
        try:
            query_embedding = get_ollama_embedding(query_text, model_to_use)
        except Exception as e:
             return jsonify({"error": f"Embedding generation failed: {str(e)}"}), 500
        
        collection = Collection(collection_name)
        collection.load()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = collection.search(data=[query_embedding], anns_field="embedding", param=search_params, limit=top_k, 
                                    output_fields=["text", "source_file", "chunk_index", "full_path"])
        
        response_data = []
        for hit in results[0]:
            response_data.append({
                "source_file": hit.entity.get("source_file"),
                "content_chunk": hit.entity.get("text"),
                "score": hit.distance,
            })
        collection.release()
        return jsonify({"related_documents": response_data})
    except Exception as e:
        logging.error(f"API /find-related error: {e}")
        return jsonify({"error": str(e)}), 500
