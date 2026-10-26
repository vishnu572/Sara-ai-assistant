import requests
import json
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import format_messages_for_chat_api, get_system_prompt

logger = logging.getLogger(__name__)

class TokenMixClient:
    """
    Dedicated client for TokenMix API.
    Configured with model 'gpt-4o-mini'.
    Supports both direct HTTP chat/completions and OpenAI-compatible client routing.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or config.TOKENMIX_API_KEY
        self.base_url = base_url or config.TOKENMIX_BASE_URL
        self.api_url = api_url or config.TOKENMIX_API_URL
        self.model = model or config.TOKENMIX_MODEL or "gpt-4o-mini"
        self.timeout = config.API_TIMEOUT

    def is_configured(self) -> bool:
        """Check if TokenMix API key is supplied."""
        return bool(self.api_key and self.api_key.strip())

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            clean_key = self.api_key.strip()
            headers["Authorization"] = f"Bearer {clean_key}"
            headers["x-api-key"] = clean_key
        return headers

    def chat(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send chat messages to TokenMix API using model gpt-4o-mini.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "TokenMix API key is not configured. Please add `TOKENMIX_API_KEY` into your `.env` file."
            }

        messages = format_messages_for_chat_api(message, history=history)

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }

        # Try Method 1: Direct HTTP request to TokenMix completions endpoint
        try:
            response = requests.post(
                self.api_url,
                headers=self.get_headers(),
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                content = None
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        content = choice["message"]["content"]
                    elif "text" in choice:
                        content = choice["text"]
                elif "response" in data:
                    content = data["response"]
                elif "output" in data:
                    content = data["output"]
                elif "text" in data:
                    content = data["text"]

                if content is not None:
                    return {
                        "success": True,
                        "text": content.strip(),
                        "model": self.model,
                        "provider": f"TokenMix ({self.model})"
                    }
                else:
                    return {
                        "success": False,
                        "error": "TokenMix returned an unexpected JSON structure."
                    }

            elif response.status_code in (401, 403):
                return {
                    "success": False,
                    "error": "TokenMix authentication failed. Please verify your TOKENMIX_API_KEY in .env."
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "TokenMix rate limit reached. Please wait a moment before sending another message."
                }
            else:
                # If direct HTTP gave 404 or other code, attempt OpenAI SDK compatible routing
                logger.warning(f"Direct TokenMix HTTP returned {response.status_code}, trying SDK client fallback...")
                return self._chat_via_openai_sdk(messages)

        except requests.Timeout:
            return {
                "success": False,
                "error": f"TokenMix request timed out after {self.timeout}s."
            }
        except requests.RequestException as e:
            logger.warning(f"Direct TokenMix HTTP error: {e}. Trying SDK client fallback...")
            return self._chat_via_openai_sdk(messages)

    def _chat_via_openai_sdk(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fallback using openai SDK with TokenMix base_url.
        """
        try:
            import openai
            client = openai.OpenAI(
                api_key=self.api_key.strip(),
                base_url=self.base_url
            )
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=self.timeout
            )
            answer = resp.choices[0].message.content or ""
            return {
                "success": True,
                "text": answer.strip(),
                "model": self.model,
                "provider": f"TokenMix ({self.model})"
            }
        except Exception as e:
            logger.error(f"TokenMix OpenAI SDK compatibility error: {e}")
            return {
                "success": False,
                "error": f"Could not connect to TokenMix API: {str(e)}"
            }
