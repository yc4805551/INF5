"""
Test cases for Remote Control API

Run with: pytest test_remote_control.py -v
"""
import pytest
import json
import io
from app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def api_key():
    """Get API key from environment."""
    import os
    return os.getenv('OPENCLAW_API_KEY', 'Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi')


@pytest.fixture
def headers(api_key):
    """Create headers with API key."""
    return {'X-API-Key': api_key, 'Content-Type': 'application/json'}


# ==================== Health & Info Tests ====================

def test_health_check(client, headers):
    """Test health check endpoint."""
    response = client.get('/api/remote-control/health', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['status'] == 'healthy'


def test_health_check_no_api_key(client):
    """Test health check fails without API key."""
    response = client.get('/api/remote-control/health')
    assert response.status_code == 401


def test_capabilities(client, headers):
    """Test capabilities endpoint."""
    response = client.get('/api/remote-control/capabilities', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'capabilities' in data['data']
    assert 'session_management' in data['data']['capabilities']


# ==================== Session Management Tests ====================

def test_create_session(client, headers):
    """Test session creation."""
    payload = {
        'session_name': 'Test Session',
        'metadata': {'test': True}
    }
    response = client.post('/api/remote-control/session/create', 
                          headers=headers, 
                          data=json.dumps(payload))
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'session_id' in data['data']
    return data['data']['session_id']


def test_get_session_status(client, headers):
    """Test getting session status."""
    # Create session first
    session_id = test_create_session(client, headers)
    
    # Get status
    response = client.get(f'/api/remote-control/session/{session_id}/status', 
                         headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['session_id'] == session_id
    assert data['data']['status'] == 'active'


def test_close_session(client, headers):
    """Test closing a session."""
    # Create session first
    session_id = test_create_session(client, headers)
    
    # Close it
    response = client.post(f'/api/remote-control/session/{session_id}/close', 
                          headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'


# ==================== Document Operations Tests ====================

def test_create_document(client, headers):
    """Test document creation from Tiptap JSON."""
    # Create session first
    session_id = test_create_session(client, headers)
    
    payload = {
        'session_id': session_id,
        'title': 'Test Document',
        'content': {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Hello World'}]
                }
            ]
        }
    }
    
    response = client.post('/api/remote-control/document/create',
                          headers=headers,
                          data=json.dumps(payload))
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'doc_id' in data['data']
    return data['data']['doc_id']


def test_get_document_content(client, headers):
    """Test getting document content."""
    doc_id = test_create_document(client, headers)
    
    response = client.get(f'/api/remote-control/document/{doc_id}/content',
                         headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['doc_id'] == doc_id
    assert 'content' in data['data']


def test_update_document_content(client, headers):
    """Test updating document content."""
    doc_id = test_create_document(client, headers)
    
    payload = {
        'content': {
            'type': 'doc',
            'content': [
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': 'Updated content'}]
                }
            ]
        }
    }
    
    response = client.put(f'/api/remote-control/document/{doc_id}/content',
                         headers=headers,
                         data=json.dumps(payload))
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'


def test_export_docx(client, headers):
    """Test exporting document as DOCX."""
    doc_id = test_create_document(client, headers)
    
    response = client.get(f'/api/remote-control/document/{doc_id}/export-docx',
                         headers=headers)
    assert response.status_code == 200
    assert response.content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


# ==================== Integration Tests ====================

def test_full_workflow(client, headers):
    """Test complete workflow: create session -> create doc -> export."""
    # 1. Create session
    session_resp = client.post('/api/remote-control/session/create',
                               headers=headers,
                               data=json.dumps({'session_name': 'Full Test'}))
    session_id = json.loads(session_resp.data)['data']['session_id']
    
    # 2. Create document
    doc_payload = {
        'session_id': session_id,
        'title': 'Integration Test',
        'content': {
            'type': 'doc',
            'content': [
                {
                    'type': 'heading',
                    'attrs': {'level': 1},
                    'content': [{'type': 'text', 'text': '测试标题'}]
                },
                {
                    'type': 'paragraph',
                    'content': [{'type': 'text', 'text': '这是测试内容。'}]
                }
            ]
        }
    }
    doc_resp = client.post('/api/remote-control/document/create',
                          headers=headers,
                          data=json.dumps(doc_payload))
    doc_id = json.loads(doc_resp.data)['data']['doc_id']
    
    # 3. Export as DOCX
    export_resp = client.get(f'/api/remote-control/document/{doc_id}/export-docx',
                            headers=headers)
    assert export_resp.status_code == 200
    
    # 4. Close session
    close_resp = client.post(f'/api/remote-control/session/{session_id}/close',
                            headers=headers)
    assert close_resp.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
