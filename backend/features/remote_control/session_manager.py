"""
Session Manager for Remote Control API

Manages OpenClaw sessions to isolate state between different tasks.
"""
import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages sessions for OpenClaw Remote Control API.
    
    Each session represents an isolated workspace with its own documents and state.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = int(os.getenv('OPENCLAW_SESSION_TIMEOUT', '3600'))  # seconds
    
    def create_session(self, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            metadata: Optional metadata to attach to the session
        
        Returns:
            Session information dict
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        
        session = {
            'session_id': session_id,
            'created_at': now.isoformat(),
            'last_activity': now.isoformat(),
            'metadata': metadata or {},
            'active_documents': [],
            'status': 'active'
        }
        
        self.sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        
        return {
            'session_id': session_id,
            'status': 'created',
            'created_at': session['created_at']
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
        
        Returns:
            Session dict or None if not found
        """
        session = self.sessions.get(session_id)
        if session:
            self._update_activity(session_id)
        return session
    
    def close_session(self, session_id: str) -> bool:
        """
        Close a session and clean up its documents.
        
        Args:
            session_id: Session ID to close
        
        Returns:
            True if session was closed, False if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Clean up documents associated with this session
        doc_ids_to_remove = [
            doc_id for doc_id, doc in self.documents.items()
            if doc.get('session_id') == session_id
        ]
        
        for doc_id in doc_ids_to_remove:
            del self.documents[doc_id]
        
        # Mark session as closed
        session['status'] = 'closed'
        session['closed_at'] = datetime.now().isoformat()
        
        logger.info(f"Closed session: {session_id}, removed {len(doc_ids_to_remove)} documents")
        
        # Optionally remove the session (keep for audit trail)
        # del self.sessions[session_id]
        
        return True
    
    def cleanup_expired_sessions(self):
        """
        Clean up sessions that have exceeded the timeout.
        """
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session['status'] != 'active':
                continue
            
            last_activity = datetime.fromisoformat(session['last_activity'])
            if (now - last_activity).total_seconds() > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            self.close_session(session_id)
    
    def _update_activity(self, session_id: str):
        """Update the last activity timestamp for a session."""
        if session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
    
    def create_document(self, session_id: str, title: str, content: Dict[str, Any]) -> str:
        """
        Create a document within a session.
        
        Args:
            session_id: Session ID
            title: Document title
            content: Tiptap JSON content
        
        Returns:
            Document ID
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        
        document = {
            'doc_id': doc_id,
            'session_id': session_id,
            'title': title,
            'content': content,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat()
        }
        
        self.documents[doc_id] = document
        self.sessions[session_id]['active_documents'].append(doc_id)
        self._update_activity(session_id)
        
        logger.info(f"Created document {doc_id} in session {session_id}")
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        doc = self.documents.get(doc_id)
        if doc:
            self._update_activity(doc['session_id'])
        return doc
    
    def update_document(self, doc_id: str, content: Dict[str, Any]) -> bool:
        """
        Update document content.
        
        Args:
            doc_id: Document ID
            content: New Tiptap JSON content
        
        Returns:
            True if updated, False if not found
        """
        if doc_id not in self.documents:
            return False
        
        self.documents[doc_id]['content'] = content
        self.documents[doc_id]['updated_at'] = datetime.now().isoformat()
        self._update_activity(self.documents[doc_id]['session_id'])
        
        logger.info(f"Updated document: {doc_id}")
        return True
    
    def list_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all documents in a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            List of document info dicts
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        return [
            {
                'doc_id': doc_id,
                'title': self.documents[doc_id]['title'],
                'created_at': self.documents[doc_id]['created_at'],
                'updated_at': self.documents[doc_id]['updated_at']
            }
            for doc_id in session['active_documents']
            if doc_id in self.documents
        ]


# Global session manager instance
session_manager = SessionManager()
