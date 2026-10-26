# Sara AI — Personal AI Chat & Voice Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask 3.0+](https://img.shields.io/badge/Framework-Flask%203.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![OS Windows 11](https://img.shields.io/badge/Platform-Windows%2011-0078d4.svg)](https://microsoft.com/windows)
[![License MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

Sara AI is a modern, intelligent, and user-friendly personal AI assistant built with Python and Flask for Windows 11. It provides two tailored interfaces: **Mode A (Simple Chat Assistant)** and **Mode B (Voice Assistant)**, alongside rich document tools (PDF compression via iLovePDF) and image enhancement (via Pillow / Hugging Face).

---

## ✨ Key Features

### 💬 Mode A: Simple Chat Assistant
- **Modern Chat Interface**: Conversational flow with user and assistant bubbles, auto-expanding inputs, and code syntax highlighting with one-click copy.
- **Persistent Chat History**: Fast local SQLite storage for saving, continuing, and deleting previous conversations.
- **Context-Aware Responses**: Multi-turn dialogue context maintained across conversation sessions.
- **Suggested Prompt Pills**: Instant starters for coding, topic explanations, text summarization, translations, and file tools.
- **Modular Slash Commands**:
  - `/help`: Display complete command guide.
  - `/ask <question>`: Query AI model directly.
  - `/summarize <text>`: Concise structured summary of long text.
  - `/translate <lang> | <text>`: Multi-language translation.
  - `/provider`: View active AI provider status safely without revealing secrets.
  - `/time` and `/date`: Check current local time and date.
  - `/clear`: Clear active chat messages.
  - `/compress` & `/enhance`: Trigger file processing workflows.
  - `/voice` & `/chat`: Seamless mode switching.

### 🎙️ Mode B: Voice Assistant
- **Dedicated Voice Interface**: Centered around an animated glowing microphone orb with real-time waveform visualizer.
- **5 Voice States**:
  1. **Idle**: "Tap the microphone to talk to Sara."
  2. **Listening**: Real-time microphone audio capture with pulsing red rings.
  3. **Processing**: Animated loading state while transcription and AI reasoning occur.
  4. **Speaking**: Glowing green audio waveform with spoken audio playback.
  5. **Error**: User-friendly notice with instant retry button.
- **Flexible Audio Pipeline**:
  - Captures microphone audio using the browser's MediaRecorder API / Web Audio API.
  - Transcribes audio on the backend using Python `SpeechRecognition`.
  - Generates spoken output using `pyttsx3` (saved to WAV for web playback) with automatic fallback to high-quality browser Web Speech synthesis (`window.speechSynthesis`).
  - Includes playback interruption, stop controls, and mute toggle.

### 📄 Smart File Processing & Result Cards
- **iLovePDF Integration**: Upload PDF documents, compress them via the official iLovePDF REST API, and download optimized files.
- **Image Enhancement**: Enhance contrast, balance colors, and sharpen clarity locally via Pillow or through Hugging Face image models.
- **Result Component**: Operation name, original filename & size, result filename & size, savings percentage, preview, and download button.
- **Security**: Built-in path traversal protection and secure file validation.

---

## 🏗️ Repository Architecture

```
Sara AI/
├── app.py                         # Flask application & API routes
├── config.py                      # Centralized environment configuration
├── requirements.txt               # Pinned Python package dependencies
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules (secrets & temp files)
├── README.md                      # Documentation & setup guide
│
├── services/                      # Modular backend services
│   ├── __init__.py
│   ├── assistant.py               # AI provider abstraction & fallback engine
│   ├── personality.py             # System prompt & conversational personality
│   ├── commands.py                # Slash command parser and executor
│   ├── huggingface_client.py      # Hugging Face Inference API client
│   ├── tokenmix_client.py         # TokenMix API client
│   ├── speech_recognition_service.py # Speech-to-text service
│   ├── text_to_speech_service.py  # pyttsx3 & audio synthesis service
│   ├── voice_service.py           # Unified voice interaction orchestrator
│   ├── image_enhancement.py       # Pillow & AI image enhancement service
│   └── ilovepdf_client.py         # iLovePDF REST API integration
│
├── database/                      # Local SQLite persistence
│   ├── __init__.py
│   └── history.py                 # Conversation & message database layer
│
├── templates/                     # Jinja2 HTML templates
│   ├── base.html                  # Base layout with settings modal & toasts
│   ├── index.html                 # Mode selection landing page
│   ├── chat.html                  # Mode A: Chat Assistant
│   └── voice.html                 # Mode B: Voice Assistant
│
├── static/                        # Frontend assets
│   ├── css/
│   │   ├── style.css              # Global styles, variables, modals, badges
│   │   ├── chat.css               # Chat feed, sidebar, code blocks, result cards
│   │   └── voice.css              # Voice visualizer, pulsing orb, waveforms
│   └── js/
│       ├── app.js                 # Global utilities & settings modal
│       ├── chat.js                # Chat logic, history, markdown rendering
│       ├── voice.js               # MediaRecorder, canvas visualizer, TTS playback
│       └── files.js               # File uploads, PDF compression, image enhancement
│
├── uploads/                       # Temporary incoming file uploads
├── outputs/                       # Safe directory for generated and processed files
│
└── tests/                         # Pytest test suite
    ├── test_assistant.py          # Assistant personality & provider tests
    ├── test_commands.py           # Command parsing & argument validation tests
    ├── test_files.py              # File validation, Pillow & path security tests
    └── test_routes.py             # Flask HTTP endpoint integration tests
```

---

## 🚀 Windows 11 Quick Start

### 1. Prerequisites
- **Windows 11** (64-bit)
- **Python 3.10+** (Python 3.12 recommended)
- A working microphone and speaker setup.

### 2. Clone and Setup Environment

Open **PowerShell** or **Windows Terminal**:

```powershell
# Navigate to the project directory
cd "d:\Projects\Sara AI"

# Create a virtual environment (if not already created)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install all required dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure API Credentials (`.env`)

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in your desired API credentials:

```ini
# AI Provider ('auto', 'huggingface', 'tokenmix', 'openai')
AI_PROVIDER=auto

# Hugging Face Inference Token (Get from https://huggingface.co/settings/tokens)
HF_TOKEN=your_huggingface_token_here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3

# TokenMix API Key (Optional)
TOKENMIX_API_KEY=your_tokenmix_key_here

# iLovePDF API Keys (Get free keys from https://developer.ilovepdf.com)
ILOVEPDF_PUBLIC_KEY=your_public_key_here
ILOVEPDF_PRIVATE_KEY=your_private_key_here
```

> **Note**: Sara AI is designed with an **intelligent local fallback engine**. Even without external cloud API keys, Sara AI will run smoothly in local offline mode for commands, local chat, Pillow image enhancement, and voice interaction!

### 4. Run the Application

```powershell
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

- Choose **Chat Assistant** for Mode A (`http://127.0.0.1:5000/chat`).
- Choose **Voice Assistant** for Mode B (`http://127.0.0.1:5000/voice`).

---

## 🧪 Running Unit Tests

Run the full pytest suite with verbose output:

```powershell
pytest tests/ -v
```

All external APIs and hardware interfaces are mocked, allowing tests to run completely offline without cost or microphone requirements.

---

## 🔒 Security Best Practices

- **Zero Secret Leakage**: API keys and tokens are stored exclusively in `.env` on the server and are never sent to the browser.
- **Path Traversal Protection**: Filename sanitization via `werkzeug.utils.secure_filename` prevents directory traversal attacks on the `/download/<filename>` route.
- **Isolated Storage**: Uploads and generated files are segregated in `uploads/` and `outputs/`.
- **Validation**: Strict file format and size limits (50MB max) prevent server overload.

---

## 📄 License

This project is licensed under the MIT License.
