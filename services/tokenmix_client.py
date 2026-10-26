import requests
import json
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import format_messages_for_chat_api, format_prompt_for_model

logger = logging.getLogger(__name__)

class TokenMixClient:
    """
    Dedicated client for TokenMix API.
    Maintains configurable URL, headers, payload, and response parser.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or config.TOKENMIX_API_KEY
        self.api_url = api_url or config.TOKENMIX_API_URL
        self.model = model or config.TOKENMIX_MODEL
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
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"
            headers["x-api-key"] = self.api_key.strip()
        return headers

    def chat(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send chat messages to TokenMix endpoint and return response."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "TokenMix API key (TOKENMIX_API_KEY) is not configured in .env."
            }

        messages = format_messages_for_chat_api(message, history=history)
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        }

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
                        "model": self.model
                    }
                else:
                    return {
                        "success": False,
                        "error": "TokenMix returned an unexpected response structure."
                    }

            elif response.status_code in (401, 403):
                return {
                    "success": False,
                    "error": "TokenMix authentication failed. Please check TOKENMIX_API_KEY in .env."
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "TokenMix rate limit reached. Please wait before retrying."
                }
            else:
                return {
                    "success": False,
                    "error": f"TokenMix API error ({response.status_code}): {response.text[:200]}"
                }

        except requests.Timeout:
            return {
                "success": False,
                "error": f"TokenMix request timed out after {self.timeout}s."
            }
        except requests.RequestException as e:
            logger.error(f"TokenMix request error: {e}")
            return {
                "success": False,
                "error": f"Could not connect to TokenMix API: {str(e)}"
            }
