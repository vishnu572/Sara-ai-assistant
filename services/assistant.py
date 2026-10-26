import os
import logging
from typing import List, Dict, Any, Optional
import config
from services.personality import generate_local_fallback_response, get_system_prompt
from services.tokenmix_client import TokenMixClient
from services.huggingface_client import HuggingFaceClient

logger = logging.getLogger(__name__)

class AssistantService:
    def __init__(self):
        # TokenMix is the primary AI replier configured with gpt-4o-mini
        self.tokenmix_client = TokenMixClient()
        self.hf_client = HuggingFaceClient()

    def get_provider_status(self) -> Dict[str, Any]:
        """
        Return the operational status of all supported AI providers without leaking keys.
        """
        tokenmix_configured = self.tokenmix_client.is_configured()
        hf_configured = self.hf_client.is_configured()

        active_preference = config.AI_PROVIDER

        if active_preference == "tokenmix":
            active_name = f"TokenMix ({config.TOKENMIX_MODEL})" if tokenmix_configured else "Local Offline (TokenMix key needed in .env)"
        elif active_preference == "huggingface":
            active_name = "Hugging Face" if hf_configured else "Local Offline (HF token missing)"
        else: # auto / default
            if tokenmix_configured:
                active_name = f"TokenMix ({config.TOKENMIX_MODEL})"
            elif hf_configured:
                active_name = "Hugging Face (Auto)"
            else:
                active_name = "Local Intelligent Engine (Offline Mode)"

        return {
            "mode": config.AI_PROVIDER,
            "active_provider": active_name,
            "primary_model": config.TOKENMIX_MODEL,
            "providers": {
                "tokenmix": {
                    "name": "TokenMix API (Primary Replier)",
                    "configured": tokenmix_configured,
                    "model": config.TOKENMIX_MODEL,
                    "endpoint": config.TOKENMIX_API_URL
                },
                "huggingface": {
                    "name": "Hugging Face Inference API",
                    "configured": hf_configured,
                    "model": config.HF_MODEL
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
        Generate response using TokenMix (gpt-4o-mini) as the primary replier.
        Falls back gracefully if external API is unreachable or keys are not provided.
        """
        provider_pref = config.AI_PROVIDER

        # 1. Primary: TokenMix API with model gpt-4o-mini
        if provider_pref in ("tokenmix", "auto"):
            if self.tokenmix_client.is_configured():
                res = self.tokenmix_client.chat(message, history=history)
                if res.get("success"):
                    return {
                        "text": res["text"],
                        "provider": f"TokenMix ({config.TOKENMIX_MODEL})",
                        "model": config.TOKENMIX_MODEL,
                        "success": True
                    }
                else:
                    logger.warning(f"TokenMix error: {res.get('error')}. Attempting fallback...")
                    # If explicit tokenmix and it failed, notify with option to fallback
                    if provider_pref == "tokenmix" and not self.hf_client.is_configured():
                        return {
                            "text": f"Sara AI encountered a TokenMix API issue: {res.get('error')}",
                            "provider": f"TokenMix ({config.TOKENMIX_MODEL} - Error)",
                            "model": config.TOKENMIX_MODEL,
                            "success": False,
                            "error": res.get("error")
                        }
            elif provider_pref == "tokenmix":
                # TokenMix chosen but no key in .env
                local_text = generate_local_fallback_response(message, history=history)
                return {
                    "text": (
                        f"{local_text}\n\n"
                        f"> 💡 *Notice: TokenMix is configured with model `{config.TOKENMIX_MODEL}`. "
                        f"To enable live cloud completions, add your `TOKENMIX_API_KEY` to the `.env` file.*"
                    ),
                    "provider": f"TokenMix ({config.TOKENMIX_MODEL} - Offline)",
                    "model": config.TOKENMIX_MODEL,
                    "success": True
                }

        # 2. Hugging Face fallback
        if self.hf_client.is_configured():
            res = self.hf_client.chat(message, history=history)
            if res.get("success"):
                return {
                    "text": res["text"],
                    "provider": "Hugging Face (Fallback)",
                    "model": config.HF_MODEL,
                    "success": True
                }
            logger.warning(f"HF failed: {res.get('error')}.")

        # 3. Intelligent Local Fallback Engine
        local_text = generate_local_fallback_response(message, history=history)
        return {
            "text": local_text,
            "provider": "Sara AI (Local Assistant)",
            "model": "Local-Rules-v1",
            "success": True
        }

# Global instance for app reuse
assistant_service = AssistantService()
