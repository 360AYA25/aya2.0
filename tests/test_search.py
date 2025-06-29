import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def make_update(command: str, user_id: int = 1) -> dict:
    return {
        "update_id": 234567,
        "message": {
            "message_id": 1,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat": {"id": user_id, "type": "private"},
            "date": 1234567890,
            "text": command,
            "entities": [{"type": "bot_command", "offset": 0, "length": len(command)}]
        }
    }

def test_search_hit():
    payload = make_update("/search python")
    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200

def test_search_miss():
    payload = make_update("/search lkjdfglskjdfgskjdg")  # редкая строка, нет совпадений
    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200

def test_search_long_query():
    query = "/search " + ("python " * 60)
    payload = make_update(query)
    resp = client.post("/webhook/telegram", json=payload)
    assert resp.status_code == 200

