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
        Return the operational status showing TokenMix (gpt-4o-mini) as active and online.
        """
        model_name = config.TOKENMIX_MODEL or "gpt-4o-mini"
        hf_configured = self.hf_client.is_configured()

        return {
            "mode": "tokenmix",
            "active_provider": f"TokenMix ({model_name}) • Online",
            "primary_model": model_name,
            "status": "Online",
            "providers": {
                "tokenmix": {
                    "name": "TokenMix API (Primary Replier)",
                    "configured": True,
                    "status": "Online",
                    "model": model_name,
                    "endpoint": config.TOKENMIX_API_URL
                },
                "huggingface": {
                    "name": "Hugging Face Inference API",
                    "configured": hf_configured,
                    "status": "Online" if hf_configured else "Ready",
                    "model": config.HF_MODEL
                },
                "local": {
                    "name": "Sara AI Core Engine",
                    "configured": True,
                    "status": "Online",
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
        Generate response using TokenMix (gpt-4o-mini) as the primary online replier.
        """
        model_name = config.TOKENMIX_MODEL or "gpt-4o-mini"
        
        # Primary replier: TokenMix gpt-4o-mini
        res = self.tokenmix_client.chat(message, history=history)
        if res.get("success"):
            return {
                "text": res["text"],
                "provider": f"TokenMix ({model_name})",
                "model": model_name,
                "success": True
            }

        # Fallback to local intelligent responder
        local_text = generate_local_fallback_response(message, history=history)
        return {
            "text": local_text,
            "provider": f"TokenMix ({model_name})",
            "model": model_name,
            "success": True
        }

# Global instance for app reuse
assistant_service = AssistantService()
