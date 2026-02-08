"""
Service layer for Remote Control API

Integrates with existing INF5 features to provide unified functionality for OpenClaw.
"""
import io
import logging
from typing import Dict, Any, Optional
from features.canvas_converter import tiptap_to_docx, docx_to_tiptap, tiptap_to_smart_docx
from features.agent_anything.services import chat_with_anything, generate_content_with_knowledge, perform_anything_audit
from .session_manager import session_manager

logger = logging.getLogger(__name__)


class RemoteControlService:
    """
    Service layer for Remote Control API.
    Provides high-level functions for document and AI operations.
    """
    
    @staticmethod
    def import_docx(session_id: str, file_stream: io.BytesIO, filename: str) -> Dict[str, Any]:
        """
        Import a DOCX file into a session.
        
        Args:
            session_id: Session ID
            file_stream: DOCX file stream
            filename: Original filename
        
        Returns:
            Document info with Tiptap JSON content
        """
        try:
            # Convert DOCX to Tiptap JSON
            tiptap_json = docx_to_tiptap(file_stream)
            
            # Create document in session
            title = filename.replace('.docx', '').replace('.DOCX', '')
            doc_id = session_manager.create_document(session_id, title, tiptap_json)
            
            logger.info(f"Imported DOCX '{filename}' as document {doc_id}")
            
            return {
                'doc_id': doc_id,
                'title': title,
                'content': tiptap_json,
                'filename': filename
            }
        except Exception as e:
            logger.error(f"Failed to import DOCX: {e}")
            raise
    
    @staticmethod
    def export_docx(doc_id: str, format_type: str = 'standard') -> io.BytesIO:
        """
        Export a document as DOCX.
        
        Args:
            doc_id: Document ID
            format_type: 'standard' or 'smart' (smart gov format)
        
        Returns:
            DOCX file stream
        """
        doc = session_manager.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")
        
        content = doc['content']
        
        if format_type == 'smart':
            docx_stream = tiptap_to_smart_docx(content)
        else:
            docx_stream = tiptap_to_docx(content)
        
        logger.info(f"Exported document {doc_id} as {format_type} DOCX")
        return docx_stream
    
    @staticmethod
    def create_document_from_json(session_id: str, title: str, content: Dict[str, Any]) -> str:
        """
        Create a document from Tiptap JSON.
        
        Args:
            session_id: Session ID
            title: Document title
            content: Tiptap JSON content
        
        Returns:
            Document ID
        """
        doc_id = session_manager.create_document(session_id, title, content)
        logger.info(f"Created document {doc_id} from JSON")
        return doc_id
    
    @staticmethod
    def chat_with_knowledge(message: str, workspace_slug: Optional[str] = None, 
                           history: Optional[list] = None, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat with AnythingLLM knowledge base.
        
        Args:
            message: User message
            workspace_slug: AnythingLLM workspace slug (optional)
            history: Chat history (optional)
            context: Additional context (optional)
        
        Returns:
            Chat response with sources
        """
        try:
            result = chat_with_anything(message, history or [], workspace_slug)
            logger.info(f"Knowledge chat completed for workspace: {workspace_slug}")
            return result
        except Exception as e:
            logger.error(f"Knowledge chat failed: {e}")
            raise
    
    @staticmethod
    def smart_write(prompt: str, workspace_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate content using knowledge base.
        
        Args:
            prompt: Writing prompt
            workspace_slug: AnythingLLM workspace slug (optional)
        
        Returns:
            Generated content with metadata
        """
        try:
            result = generate_content_with_knowledge(prompt)
            logger.info(f"Smart write completed: {len(result.get('content', ''))} chars")
            return result
        except Exception as e:
            logger.error(f"Smart write failed: {e}")
            raise
    
    @staticmethod
    def audit_document(doc_id: str, rules: Optional[str] = None) -> Dict[str, Any]:
        """
        Audit a document for errors and improvements.
        
        Args:
            doc_id: Document ID
            rules: Custom audit rules (optional)
        
        Returns:
            Audit results
        """
        doc = session_manager.get_document(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")
        
        # Extract text from Tiptap JSON
        def extract_text(content):
            """Recursively extract text from Tiptap JSON."""
            if isinstance(content, dict):
                if content.get('type') == 'text':
                    return content.get('text', '')
                if 'content' in content:
                    return extract_text(content['content'])
            elif isinstance(content, list):
                return '\n'.join(extract_text(item) for item in content)
            return ''
        
        text = extract_text(doc['content'])
        
        try:
            result = perform_anything_audit(
                target_text=text,
                source_context='',
                rules=rules or '检查语法、格式、逻辑问题'
            )
            logger.info(f"Audit completed for document {doc_id}")
            return result
        except Exception as e:
            logger.error(f"Audit failed: {e}")
            raise


# Singleton instance
remote_service = RemoteControlService()
