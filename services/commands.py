import re
from datetime import datetime
from typing import Dict, Any, Optional
import config
from services.assistant import assistant_service

HELP_TEXT = r"""### 🤖 Sara AI Command Guide

Here are the supported commands you can run anytime:

| Command | Description | Example |
| :--- | :--- | :--- |
| `/help` | Show this list of available commands | `/help` |
| `/ask <question>` | Ask Sara AI a direct question | `/ask What is gradient descent?` |
| `/summarize <text>` | Summarize any provided text | `/summarize Artificial Intelligence is...` |
| `/translate <lang> \| <text>` | Translate text into requested language | `/translate Spanish \| Good morning Sara!` |
| `/provider` | View configured AI provider status | `/provider` |
| `/time` | Display the current local time | `/time` |
| `/date` | Display the current local date | `/date` |
| `/clear` | Clear the current conversation messages | `/clear` |
| `/voice` | Navigate to the Voice Assistant | `/voice` |
| `/chat` | Navigate to the Chat Assistant | `/chat` |
| `/compress` | Start the PDF compression workflow | `/compress` (attach PDF or drop file) |
| `/enhance` | Start image enhancement workflow | `/enhance` (attach image or drop file) |
"""

def is_command(text: str) -> bool:
    """Check if the input text starts with a slash command."""
    if not text:
        return False
    return text.strip().startswith("/")

def parse_command(text: str) -> Dict[str, Any]:
    """Parse a slash command string into command name and arguments."""
    clean = text.strip()
    if not clean.startswith("/"):
        return {"is_command": False}
    
    parts = clean.split(maxsplit=1)
    cmd_name = parts[0][1:].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    
    return {
        "is_command": True,
        "command": cmd_name,
        "args": args,
        "raw": text
    }

def execute_command(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a supported command and return a standardized result object.
    Does not crash on missing arguments.
    """
    parsed = parse_command(text)
    if not parsed["is_command"]:
        return {
            "success": False,
            "error": "Not a command",
            "text": "The provided text is not a command."
        }
    
    cmd = parsed["command"]
    args = parsed["args"]

    # 1. /help
    if cmd == "help":
        return {
            "success": True,
            "command": "help",
            "text": HELP_TEXT,
            "action": None
        }

    # 2. /ask <question>
    if cmd == "ask":
        if not args:
            return {
                "success": False,
                "command": "ask",
                "text": "⚠️ **Missing question**.\n\nUsage: `/ask <your question>`\n*Example:* `/ask How does recursion work in Python?`"
            }
        ai_resp = assistant_service.generate_response(args)
        return {
            "success": ai_resp.get("success", True),
            "command": "ask",
            "text": ai_resp.get("text", ""),
            "provider": ai_resp.get("provider", "Sara AI")
        }

    # 3. /summarize <text>
    if cmd == "summarize":
        if not args:
            return {
                "success": False,
                "command": "summarize",
                "text": "⚠️ **Missing text to summarize**.\n\nUsage: `/summarize <text>`\n*Example:* `/summarize Machine learning is a field of inquiry devoted to understanding and building methods that learn...`"
            }
        prompt = f"Please provide a concise, structured summary of the following text with key points:\n\n{args}"
        ai_resp = assistant_service.generate_response(prompt)
        return {
            "success": ai_resp.get("success", True),
            "command": "summarize",
            "text": f"### 📝 Summary\n\n{ai_resp.get('text', '')}",
            "provider": ai_resp.get("provider", "Sara AI")
        }

    # 4. /translate <language> | <text>
    if cmd == "translate":
        if not args:
            return {
                "success": False,
                "command": "translate",
                "text": "⚠️ **Missing arguments for translation**.\n\nUsage: `/translate <language> | <text>`\n*Example:* `/translate Spanish | Welcome to our meeting today.`"
            }
        
        # Check for pipe separator first, or fallback to space
        target_lang = ""
        source_text = ""
        if "|" in args:
            lang_part, text_part = args.split("|", 1)
            target_lang = lang_part.strip()
            source_text = text_part.strip()
        elif " " in args:
            parts = args.split(" ", 1)
            target_lang = parts[0].strip()
            source_text = parts[1].strip()
            
        if not target_lang or not source_text:
            return {
                "success": False,
                "command": "translate",
                "text": "⚠️ **Invalid translation format**.\n\nUsage: `/translate <language> | <text>`\n*Example:* `/translate Japanese | Thank you very much.`"
            }
            
        prompt = f"Translate the following text into {target_lang}. Provide only the accurate translation followed by pronunciation if applicable:\n\n{source_text}"
        ai_resp = assistant_service.generate_response(prompt)
        return {
            "success": ai_resp.get("success", True),
            "command": "translate",
            "text": f"### 🌐 Translation ({target_lang})\n\n{ai_resp.get('text', '')}",
            "provider": ai_resp.get("provider", "Sara AI")
        }

    # 5. /provider
    if cmd == "provider":
        status = assistant_service.get_provider_status()
        providers = status["providers"]
        
        text_lines = [
            "### ⚙️ Sara AI Provider Status\n",
            f"- **Configured Mode**: `{status['mode']}`",
            f"- **Active Provider**: **{status['active_provider']}**\n",
            "| Provider | Status | Configured Model |",
            "| :--- | :--- | :--- |",
            f"| Hugging Face | {'✅ Configured' if providers['huggingface']['configured'] else '❌ Not Configured'} | `{providers['huggingface']['model']}` |",
            f"| TokenMix | {'✅ Configured' if providers['tokenmix']['configured'] else '❌ Not Configured'} | `{providers['tokenmix']['model']}` |",
            f"| OpenAI (Compat) | {'✅ Configured' if providers['openai']['configured'] else '❌ Not Configured'} | `{providers['openai']['model']}` |",
            f"| Local Engine | ✅ Active (Fallback) | `{providers['local']['model']}` |\n",
            "> *Note: API keys are securely loaded from your local `.env` and never displayed.*"
        ]
        return {
            "success": True,
            "command": "provider",
            "text": "\n".join(text_lines),
            "status": status
        }

    # 6. /time
    if cmd == "time":
        now_time = datetime.now().strftime("%I:%M:%S %p")
        return {
            "success": True,
            "command": "time",
            "text": f"🕒 **Current Local Time**: `{now_time}`"
        }

    # 7. /date
    if cmd == "date":
        now_date = datetime.now().strftime("%A, %B %d, %Y")
        return {
            "success": True,
            "command": "date",
            "text": f"📅 **Current Date**: `{now_date}`"
        }

    # 8. /clear
    if cmd == "clear":
        return {
            "success": True,
            "command": "clear",
            "action": "clear_conversation",
            "text": "Conversation cleared."
        }

    # 9. /voice
    if cmd == "voice":
        return {
            "success": True,
            "command": "voice",
            "action": "navigate",
            "url": "/voice",
            "text": "Switching to Voice Assistant mode..."
        }

    # 10. /chat
    if cmd == "chat":
        return {
            "success": True,
            "command": "chat",
            "action": "navigate",
            "url": "/chat",
            "text": "Switching to Chat Assistant mode..."
        }

    # 11. /compress
    if cmd == "compress":
        return {
            "success": True,
            "command": "compress",
            "action": "open_pdf_modal",
            "text": "Please attach or select a PDF file to compress with iLovePDF."
        }

    # 12. /enhance
    if cmd == "enhance":
        return {
            "success": True,
            "command": "enhance",
            "action": "open_image_modal",
            "text": "Please attach or select an image file to enhance."
        }

    # Unknown command
    return {
        "success": False,
        "command": cmd,
        "text": f"❓ Unknown command `/{cmd}`. Type `/help` to see all available commands."
    }
