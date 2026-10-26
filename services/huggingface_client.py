import requests
import json
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import format_prompt_for_model, get_system_prompt

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    def __init__(self, token: Optional[str] = None, model: Optional[str] = None):
        self.token = token or config.HF_TOKEN
        self.model = model or config.HF_MODEL
        self.api_url = config.HF_API_URL.rstrip("/") + "/" + self.model
        self.timeout = config.API_TIMEOUT

    def is_configured(self) -> bool:
        """Check if Hugging Face token is provided and non-empty."""
        return bool(self.token and self.token.strip())

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token.strip()}"
        return headers

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        """Send generation request to Hugging Face Inference API."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Hugging Face API token (HF_TOKEN) is not configured in .env."
            }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
                "do_sample": True
            },
            "options": {
                "wait_for_model": True
            }
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
                generated_text = ""
                if isinstance(data, list) and len(data) > 0:
                    generated_text = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    generated_text = data.get("generated_text", "") or data.get("summary_text", "")
                
                # Clean up any trailing end tokens
                cleaned_text = generated_text.replace("</s>", "").replace("<|im_end|>", "").strip()
                return {
                    "success": True,
                    "text": cleaned_text,
                    "model": self.model
                }
            
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "Invalid Hugging Face API token. Please verify HF_TOKEN in .env."
                }
            elif response.status_code == 429:
                return {
                    "success": False,
                    "error": "Hugging Face rate limit exceeded. Please wait a moment or switch provider."
                }
            elif response.status_code == 503:
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                estimated = data.get("estimated_time", 20)
                return {
                    "success": False,
                    "error": f"Hugging Face model is currently loading (est. {int(estimated)}s). Please retry shortly."
                }
            else:
                return {
                    "success": False,
                    "error": f"Hugging Face API error ({response.status_code}): {response.text[:200]}"
                }

        except requests.Timeout:
            return {
                "success": False,
                "error": f"Hugging Face API request timed out after {self.timeout}s."
            }
        except requests.RequestException as e:
            logger.error(f"HF request exception: {e}")
            return {
                "success": False,
                "error": f"Network error connecting to Hugging Face: {str(e)}"
            }

    def chat(self, message: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Format chat history with system prompt and invoke generation."""
        formatted_prompt = format_prompt_for_model(message, history=history)
        return self.generate(formatted_prompt)
