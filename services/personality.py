import re
from typing import List, Dict, Any, Optional

SARA_SYSTEM_PROMPT = """You are Sara AI, a helpful personal AI assistant.

Your job is to help users with questions, programming, education, writing, productivity, language translation, and supported file operations.

Respond naturally and directly to the user's request.

Understand the context of previous messages and use it when relevant.

Do not give generic greetings when the user asks a specific question.

Keep answers concise unless the user asks for details.

For technical questions, explain concepts step by step and provide working examples when appropriate.

For coding tasks, provide correct code and explain where files belong.

For file-processing requests, clearly explain what operation will be performed.

Never claim to have completed an action unless it actually succeeded.

If a required API is unavailable, explain the issue and offer an appropriate alternative.

Protect API keys, private files, and user data.

Never invent API results, file downloads, or successful operations."""

def get_system_prompt() -> str:
    """Return the master system prompt defining Sara AI's personality."""
    return SARA_SYSTEM_PROMPT.strip()

def format_prompt_for_model(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    Format conversation history and current prompt into an instructional prompt string.
    Suitable for raw completion / instruction models like Mistral / LLaMA / Zephyr.
    """
    sys_prompt = system_prompt or get_system_prompt()
    lines = [f"<|system|>\n{sys_prompt}\n"]
    
    if history:
        for item in history[-8:]:  # keep last 8 turns for context window efficiency
            role = item.get("role", "user")
            content = item.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                lines.append(f"<|user|>\n{content}\n")
            elif role == "assistant":
                lines.append(f"<|assistant|>\n{content}\n")
    
    lines.append(f"<|user|>\n{message}\n<|assistant|>\n")
    return "\n".join(lines)

def format_messages_for_chat_api(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Format history and message into standard OpenAI/TokenMix style chat message dicts.
    """
    sys_prompt = system_prompt or get_system_prompt()
    messages = [{"role": "system", "content": sys_prompt}]
    
    if history:
        for item in history[-10:]:
            role = item.get("role")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
                
    messages.append({"role": "user", "content": message})
    return messages

def generate_local_fallback_response(message: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Provide intelligent, context-aware local responses when external AI APIs are not configured or offline.
    Ensures Sara AI is functional and friendly out of the box on Windows 11.
    """
    msg_lower = message.lower().strip()
    
    # Greetings
    if re.match(r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b", msg_lower):
        return (
            "Hello! I am Sara AI, your personal AI assistant. I'm ready to assist you with "
            "questions, coding, document processing, voice commands, and summaries. "
            "How can I help you today?"
        )
    
    # Who are you / Identity
    if "who are you" in msg_lower or "what can you do" in msg_lower or "your name" in msg_lower:
        return (
            "I'm **Sara AI**, your personal AI companion and productivity assistant.\n\n"
            "Here is what I can do for you:\n"
            "- **Smart Chat & Q&A**: Answer questions, write Python code, explain concepts, and brainstorm ideas.\n"
            "- **Voice Assistant**: Real-time voice interaction with speech recognition and spoken text-to-speech.\n"
            "- **Commands**: Run quick utilities like `/summarize`, `/translate`, `/date`, `/time`, `/provider`, and `/help`.\n"
            "- **PDF Processing**: Compress and optimize PDF files using the integrated iLovePDF engine.\n"
            "- **Image Enhancement**: Enhance, balance, and sharpen images locally with Pillow or via AI.\n\n"
            "Try asking me a question or typing `/help` to see all available commands!"
        )

    # Coding help request
    if "python" in msg_lower or "code" in msg_lower or "function" in msg_lower or "script" in msg_lower:
        return (
            "I'd be glad to help you with programming! Here is an example of what I can help you build in Python:\n\n"
            "```python\n"
            "# Example: Simple task timer in Python\n"
            "import time\n\n"
            "def countdown(seconds: int):\n"
            "    while seconds > 0:\n"
            "        mins, secs = divmod(seconds, 60)\n"
            "        print(f'{mins:02d}:{secs:02d}', end='\\r')\n"
            "        time.sleep(1)\n"
            "        seconds -= 1\n"
            "    print('Time is up!')\n"
            "```\n\n"
            "Let me know what specific script or logic you are working on, and I'll write it for you step by step."
        )

    # Summarize / translate hints
    if msg_lower.startswith("summarize") or msg_lower.startswith("/summarize"):
        return (
            "To summarize text, you can use the `/summarize` command followed by the text you want summarized:\n\n"
            "`/summarize <paste your text here>`"
        )
    
    if msg_lower.startswith("translate") or msg_lower.startswith("/translate"):
        return (
            "To translate text, you can use the `/translate` command:\n\n"
            "`/translate French | Hello, how are you today?`"
        )
        
    # File help
    if "file" in msg_lower or "pdf" in msg_lower or "image" in msg_lower:
        return (
            "You can upload files directly using the paperclip button below or the File Tools panel in the sidebar.\n\n"
            "- **PDF Files**: Compress and optimize PDFs via the `/compress` command or file upload.\n"
            "- **Images**: Enhance clarity, contrast, and balance via `/enhance` or the upload tool."
        )

    # Fallback general response
    return (
        f"I received your request: \"{message}\"\n\n"
        "I am currently operating with local processing. If you have an API key for "
        "**Hugging Face** (`HF_TOKEN`) or **TokenMix** (`TOKENMIX_API_KEY`), you can add them to your `.env` "
        "file to unlock full cloud LLM generative answers.\n\n"
        "You can also use commands like `/help`, `/time`, `/date`, `/provider`, or upload a PDF/image for processing!"
    )
