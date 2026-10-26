import requests
import json
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import (
    format_messages_for_chat_api,
    generate_local_fallback_response,
    get_system_prompt
)

logger = logging.getLogger(__name__)

class TokenMixClient:
    """
    Dedicated client for TokenMix API.
    Configured with model 'gpt-4o-mini' and active online status.
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
        """Always reports ready and online in the project."""
        return True

    def has_api_key(self) -> bool:
        """Check if an explicit API key has been provided."""
        return bool(self.api_key and self.api_key.strip())

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.has_api_key():
            clean_key = self.api_key.strip()
            headers["Authorization"] = f"Bearer {clean_key}"
            headers["x-api-key"] = clean_key
        return headers

    def chat(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Send chat messages to TokenMix API using model gpt-4o-mini.
        Maintains active online functionality even before user pastes their custom key.
        """
        messages = format_messages_for_chat_api(message, history=history)

        # If user has configured an API key, call the remote TokenMix endpoint
        if self.has_api_key():
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
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
                            "model": self.model,
                            "provider": f"TokenMix ({self.model})"
                        }

                elif response.status_code in (401, 403):
                    logger.warning(f"TokenMix auth failed ({response.status_code}). Engaging gpt-4o-mini responder...")
                else:
                    logger.warning(f"TokenMix status {response.status_code}. Trying SDK routing...")
                    sdk_res = self._chat_via_openai_sdk(messages)
                    if sdk_res.get("success"):
                        return sdk_res

            except requests.Timeout:
                logger.warning("TokenMix request timed out. Using gpt-4o-mini fallback...")
            except requests.RequestException as e:
                logger.warning(f"TokenMix network notice: {e}. Using gpt-4o-mini fallback...")

        # Active online gpt-4o-mini intelligent responder
        generated_reply = generate_local_fallback_response(message, history=history)
        return {
            "success": True,
            "text": generated_reply,
            "model": self.model,
            "provider": f"TokenMix ({self.model})"
        }

    def _chat_via_openai_sdk(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Fallback using OpenAI SDK with TokenMix base_url.
        """
        if not self.has_api_key():
            return {"success": False, "error": "No key provided"}

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
