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
    """Verify TokenMix client operates online even before custom key is provided."""
    client = TokenMixClient(api_key="")
    assert not client.has_api_key()
    assert client.is_configured()
    res = client.chat("Hello")
    assert res["success"] is True
    assert res["model"] == "gpt-4o-mini"

def test_tokenmix_client_gpt_4o_mini_model():
    """Verify TokenMix client uses model gpt-4o-mini."""
    client = TokenMixClient(api_key="mock_key", model="gpt-4o-mini")
    assert client.model == "gpt-4o-mini"
    assert client.is_configured()

@patch("services.tokenmix_client.requests.post")
def test_tokenmix_chat_success(mock_post):
    """Test successful TokenMix chat completion with gpt-4o-mini."""
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Hello! I am Sara AI, powered by TokenMix gpt-4o-mini."
                }
            }
        ]
    }

    client = TokenMixClient(api_key="mock_tokenmix_key", model="gpt-4o-mini")
    res = client.chat("Hello!")
    assert res["success"] is True
    assert "TokenMix gpt-4o-mini" in res["text"]
    assert res["model"] == "gpt-4o-mini"

def test_assistant_provider_status_safe():
    """Verify provider status endpoint does not leak secrets."""
    service = AssistantService()
    status = service.get_provider_status()
    assert "active_provider" in status
    assert "providers" in status
    assert "tokenmix" in status["providers"]
    assert status["providers"]["tokenmix"]["model"] == "gpt-4o-mini"
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
