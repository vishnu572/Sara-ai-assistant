import os
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import generate_local_fallback_response, get_system_prompt
from services.huggingface_client import HuggingFaceClient
from services.tokenmix_client import TokenMixClient

logger = logging.getLogger(__name__)

class AssistantService:
    def __init__(self):
        self.hf_client = HuggingFaceClient()
        self.tokenmix_client = TokenMixClient()

    def get_provider_status(self) -> Dict[str, Any]:
        """
        Return the operational status of all supported AI providers without leaking keys.
        """
        hf_configured = self.hf_client.is_configured()
        tokenmix_configured = self.tokenmix_client.is_configured()
        openai_configured = bool(config.OPENAI_API_KEY and config.OPENAI_API_KEY.strip())

        active_preference = config.AI_PROVIDER

        if active_preference == "huggingface":
            active_name = "Hugging Face" if hf_configured else "Local Offline (HF token missing)"
        elif active_preference == "tokenmix":
            active_name = "TokenMix" if tokenmix_configured else "Local Offline (TokenMix key missing)"
        elif active_preference == "openai":
            active_name = "OpenAI" if openai_configured else "Local Offline (OpenAI key missing)"
        else: # auto
            if hf_configured:
                active_name = "Hugging Face (Auto)"
            elif tokenmix_configured:
                active_name = "TokenMix (Auto)"
            elif openai_configured:
                active_name = "OpenAI (Auto)"
            else:
                active_name = "Local Intelligent Engine (Offline Mode)"

        return {
            "mode": config.AI_PROVIDER,
            "active_provider": active_name,
            "providers": {
                "huggingface": {
                    "name": "Hugging Face Inference API",
                    "configured": hf_configured,
                    "model": config.HF_MODEL
                },
                "tokenmix": {
                    "name": "TokenMix API",
                    "configured": tokenmix_configured,
                    "model": config.TOKENMIX_MODEL
                },
                "openai": {
                    "name": "OpenAI Compatibility API",
                    "configured": openai_configured,
                    "model": config.OPENAI_MODEL
                },
                "local": {
                    "name": "Sara AI Local Assistant",
                    "configured": True,
                    "model": "Sara-RuleEngine-v1"
                }
            }
        }

    def generate_response(
        self,
        message: str,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate response based on provider configuration, fallback policy, and history.
        """
        provider_pref = config.AI_PROVIDER

        # 1. Hugging Face explicit
        if provider_pref == "huggingface":
            if self.hf_client.is_configured():
                res = self.hf_client.chat(message, history=history)
                if res.get("success"):
                    return {
                        "text": res["text"],
                        "provider": "Hugging Face",
                        "model": res.get("model", config.HF_MODEL),
                        "success": True
                    }
                else:
                    return {
                        "text": f"Sara AI encountered a Hugging Face provider issue: {res.get('error')}",
                        "provider": "Hugging Face (Error)",
                        "model": config.HF_MODEL,
                        "success": False,
                        "error": res.get("error")
                    }
            else:
                return {
                    "text": "Hugging Face is selected as the primary provider, but `HF_TOKEN` is not set in `.env`.",
                    "provider": "Configuration Warning",
                    "model": config.HF_MODEL,
                    "success": False
                }

        # 2. TokenMix explicit
        if provider_pref == "tokenmix":
            if self.tokenmix_client.is_configured():
                res = self.tokenmix_client.chat(message, history=history)
                if res.get("success"):
                    return {
                        "text": res["text"],
                        "provider": "TokenMix",
                        "model": res.get("model", config.TOKENMIX_MODEL),
                        "success": True
                    }
                else:
                    return {
                        "text": f"Sara AI encountered a TokenMix provider issue: {res.get('error')}",
                        "provider": "TokenMix (Error)",
                        "model": config.TOKENMIX_MODEL,
                        "success": False,
                        "error": res.get("error")
                    }
            else:
                return {
                    "text": "TokenMix is selected as the primary provider, but `TOKENMIX_API_KEY` is not set in `.env`.",
                    "provider": "Configuration Warning",
                    "model": config.TOKENMIX_MODEL,
                    "success": False
                }

        # 3. AUTO mode with graceful fallback policy
        # Priority order: Hugging Face -> TokenMix -> OpenAI -> Local Fallback
        if self.hf_client.is_configured():
            res = self.hf_client.chat(message, history=history)
            if res.get("success"):
                return {
                    "text": res["text"],
                    "provider": "Hugging Face",
                    "model": res.get("model", config.HF_MODEL),
                    "success": True
                }
            logger.warning(f"HF failed in auto mode: {res.get('error')}. Attempting fallback...")

        if self.tokenmix_client.is_configured():
            res = self.tokenmix_client.chat(message, history=history)
            if res.get("success"):
                return {
                    "text": res["text"],
                    "provider": "TokenMix (Fallback)",
                    "model": res.get("model", config.TOKENMIX_MODEL),
                    "success": True
                }
            logger.warning(f"TokenMix failed in auto mode: {res.get('error')}.")

        # If OpenAI key is set, try it as a secondary provider
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY.strip():
            try:
                import openai
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY.strip())
                messages = [
                    {"role": "system", "content": get_system_prompt()}
                ]
                if history:
                    for h in history[-8:]:
                        if h.get("role") in ("user", "assistant") and h.get("content"):
                            messages.append({"role": h["role"], "content": h["content"]})
                messages.append({"role": "user", "content": message})
                
                resp = client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=messages,
                    timeout=config.API_TIMEOUT
                )
                answer = resp.choices[0].message.content or ""
                return {
                    "text": answer.strip(),
                    "provider": "OpenAI",
                    "model": config.OPENAI_MODEL,
                    "success": True
                }
            except Exception as e:
                logger.error(f"OpenAI error in auto fallback: {e}")

        # Local intelligent fallback responder
        local_text = generate_local_fallback_response(message, history=history)
        return {
            "text": local_text,
            "provider": "Sara AI (Local Assistant)",
            "model": "Local-Rules-v1",
            "success": True
        }

# Global instance for app reuse
assistant_service = AssistantService()
