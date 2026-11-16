import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# File storage folders
if os.getenv("VERCEL") == "1":
    STORAGE_DIR = Path("/tmp/sara-ai")
else:
    STORAGE_DIR = BASE_DIR

UPLOAD_FOLDER = os.path.join(STORAGE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(STORAGE_DIR, "outputs")
DATABASE_PATH = os.path.join(STORAGE_DIR, "database", "sara_ai.db")

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Secret configuration
SECRET_KEY = os.getenv("SECRET_KEY", "sara-ai-local-secret-key-2026")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}
ALLOWED_PDF_EXTENSIONS = {"pdf"}
ALLOWED_AUDIO_EXTENSIONS = {"wav", "mp3", "ogg", "webm", "m4a"}
ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS | ALLOWED_PDF_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS | {"txt", "md", "json"}
)

# AI Provider Configuration
# Supported values: 'tokenmix' (default primary), 'auto', 'huggingface', 'openai'
AI_PROVIDER = os.getenv("AI_PROVIDER", "tokenmix").lower()

# Hugging Face Settings
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
HF_API_URL = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/")
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev")

# TokenMix Settings (Primary Replier with gpt-4o-mini)
TOKENMIX_API_KEY = os.getenv("TOKENMIX_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
TOKENMIX_BASE_URL = os.getenv("TOKENMIX_BASE_URL", "https://api.tokenmix.ai/v1").rstrip("/")
TOKENMIX_API_URL = os.getenv("TOKENMIX_API_URL", f"{TOKENMIX_BASE_URL}/chat/completions")
TOKENMIX_MODEL = os.getenv("TOKENMIX_MODEL", "gpt-4o-mini")

# OpenAI Settings (optional compatibility provider)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Image Enhancement Configuration
# 'auto', 'pillow', 'huggingface'
IMAGE_ENHANCE_PROVIDER = os.getenv("IMAGE_ENHANCE_PROVIDER", "auto").lower()

# iLovePDF Settings
ILOVEPDF_PUBLIC_KEY = os.getenv("ILOVEPDF_PUBLIC_KEY", "")
ILOVEPDF_PRIVATE_KEY = os.getenv("ILOVEPDF_PRIVATE_KEY", "")

# Voice Settings
TTS_RATE = int(os.getenv("TTS_RATE", "180"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))
SPEECH_LANGUAGE = os.getenv("SPEECH_LANGUAGE", "en-US")

# Network timeouts in seconds
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
