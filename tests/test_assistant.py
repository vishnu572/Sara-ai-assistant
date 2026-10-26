import pytest
from unittest.mock import patch, MagicMock
from services.personality import get_system_prompt, format_prompt_for_model, generate_local_fallback_response
from services.assistant import AssistantService
from services.huggingface_client import HuggingFaceClient
from services.tokenmix_client import TokenMixClient

def test_system_prompt_content():
    """Verify system prompt contains Sara AI personality directives."""
    prompt = get_system_prompt()
    assert "Sara AI" in prompt
    assert "helpful personal AI assistant" in prompt
    assert "Protect API keys" in prompt

def test_format_prompt_for_model():
    """Verify conversation formatting with history."""
    history = [
        {"role": "user", "content": "Hello Sara"},
        {"role": "assistant", "content": "Hello! How can I assist you?"}
    ]
    formatted = format_prompt_for_model("What is Python?", history=history)
    assert "<|user|>\nHello Sara" in formatted
    assert "<|assistant|>\nHello! How can I assist you?" in formatted
    assert "<|user|>\nWhat is Python?" in formatted

def test_local_fallback_response():
    """Verify local fallback handles greetings and questions gracefully without external APIs."""
    greeting_res = generate_local_fallback_response("Hello")
    assert "Sara AI" in greeting_res

    code_res = generate_local_fallback_response("Can you help me with python code?")
    assert "```python" in code_res

def test_huggingface_client_missing_key():
    """Verify Hugging Face client handles missing token cleanly."""
    client = HuggingFaceClient(token="")
    assert not client.is_configured()
    res = client.chat("Test message")
    assert res["success"] is False
    assert "not configured" in res["error"]

def test_tokenmix_client_missing_key():
    """Verify TokenMix client handles missing API key cleanly."""
    client = TokenMixClient(api_key="")
    assert not client.is_configured()
    res = client.chat("Test message")
    assert res["success"] is False
    assert "not configured" in res["error"]

def test_assistant_provider_status_safe():
    """Verify provider status endpoint does not leak secrets."""
    service = AssistantService()
    status = service.get_provider_status()
    assert "active_provider" in status
    assert "providers" in status
    # Verify no raw API keys are exposed
    for key, p in status["providers"].items():
        assert "token" not in p
        assert "api_key" not in p
        assert "private_key" not in p

@patch("services.huggingface_client.requests.post")
def test_assistant_huggingface_mock(mock_post):
    """Test successful Hugging Face chat completion."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = [{"generated_text": "This is a response from Sara AI."}]

    client = HuggingFaceClient(token="mock_hf_token")
    assert client.is_configured()
    res = client.chat("Hello!")
    assert res["success"] is True
    assert "This is a response from Sara AI." in res["text"]
