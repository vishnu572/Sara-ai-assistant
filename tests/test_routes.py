import pytest
import json
from app import app
from database.history import init_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """GET / should return 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Sara AI" in response.data

def test_chat_route(client):
    """GET /chat should return 200 OK."""
    response = client.get("/chat")
    assert response.status_code == 200
    assert b"Chat Assistant" in response.data

def test_voice_route(client):
    """GET /voice should return 200 OK."""
    response = client.get("/voice")
    assert response.status_code == 200
    assert b"Voice Assistant" in response.data

def test_status_endpoint(client):
    """GET /api/status should return health and provider status."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "ai_status" in data
    assert "voice_capabilities" in data

def test_api_chat_flow(client):
    """POST /api/chat with valid input should return assistant response."""
    response = client.post(
        "/api/chat",
        data=json.dumps({"message": "Hello Sara!"}),
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "response" in data
    assert "conversation_id" in data

def test_api_chat_empty_message(client):
    """POST /api/chat with empty message should return 400 Bad Request."""
    response = client.post(
        "/api/chat",
        data=json.dumps({"message": ""}),
        content_type="application/json"
    )
    assert response.status_code == 400

def test_api_command_execution(client):
    """POST /api/command with /time should succeed."""
    response = client.post(
        "/api/command",
        data=json.dumps({"command": "/time"}),
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "Current Local Time" in data["text"]

def test_conversation_history_endpoints(client):
    """Test full CRUD on /api/history."""
    # 1. Create conversation
    create_resp = client.post(
        "/api/history",
        data=json.dumps({"title": "Test Chat Session"}),
        content_type="application/json"
    )
    assert create_resp.status_code == 200
    conv_id = create_resp.get_json()["id"]

    # 2. List conversations
    list_resp = client.get("/api/history")
    assert list_resp.status_code == 200
    convs = list_resp.get_json()["conversations"]
    assert any(c["id"] == conv_id for c in convs)

    # 3. Get single conversation
    single_resp = client.get(f"/api/history/{conv_id}")
    assert single_resp.status_code == 200
    assert single_resp.get_json()["conversation"]["id"] == conv_id

    # 4. Delete conversation
    del_resp = client.delete(f"/api/history/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True

def test_download_path_traversal_blocked(client):
    """GET /download with malicious traversal should return 400 or 404."""
    response = client.get("/download/..%2f..%2fconfig.py")
    assert response.status_code in (400, 404)
