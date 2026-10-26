import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

import config
from database.history import (
    init_db,
    create_conversation,
    get_conversations,
    get_conversation,
    add_message,
    delete_conversation,
    clear_conversation_messages,
)
from services import (
    assistant_service,
    is_command,
    execute_command,
    speech_recognition_service,
    text_to_speech_service,
    voice_service,
    ilovepdf_client,
    image_enhancement_service,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SaraAI")

# Create Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

# Initialize database tables on startup
init_db()

def is_safe_filename(filename: str) -> bool:
    """Ensure filename has no path traversal components."""
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        return False
    return True

# ==========================================================
# PAGE NAVIGATION ROUTES
# ==========================================================

@app.route("/")
def index():
    """Landing page offering quick access to Chat or Voice mode."""
    status = assistant_service.get_provider_status()
    return render_template("index.html", status=status)

@app.route("/chat")
def chat_mode():
    """Mode A: Modern Simple Chat Assistant."""
    conversations = get_conversations()
    status = assistant_service.get_provider_status()
    return render_template("chat.html", conversations=conversations, status=status)

@app.route("/voice")
def voice_mode():
    """Mode B: Dedicated Voice Assistant."""
    status = assistant_service.get_provider_status()
    return render_template("voice.html", status=status)

# ==========================================================
# CHAT & COMMAND API ROUTES
# ==========================================================

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Process incoming chat message:
    - Detects and runs slash commands if present.
    - Otherwise passes conversation history to AI assistant.
    - Persists messages in SQLite database.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({"success": False, "error": "Message content cannot be empty."}), 400

    if not conversation_id:
        conversation_id = create_conversation(title=message[:30])

    # Check for slash command
    if is_command(message):
        cmd_result = execute_command(message, context={"conversation_id": conversation_id})
        
        # Save command execution to history
        add_message(conversation_id, "user", message)
        add_message(
            conversation_id,
            "assistant",
            cmd_result.get("text", ""),
            metadata={"is_command": True, "command": cmd_result.get("command")}
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "is_command": True,
            "response": cmd_result.get("text", ""),
            "action": cmd_result.get("action"),
            "url": cmd_result.get("url"),
            "provider": "Sara Command System"
        })

    # Standard conversational turn
    # Retrieve past messages for context
    conv_data = get_conversation(conversation_id)
    history = conv_data.get("messages", []) if conv_data else []

    # Save user message
    add_message(conversation_id, "user", message)

    # Generate assistant response
    ai_result = assistant_service.generate_response(message, history=history)
    reply_text = ai_result.get("text", "I am having trouble answering right now.")
    provider_used = ai_result.get("provider", "Sara AI")
    model_used = ai_result.get("model", "Default")

    # Save assistant message
    add_message(
        conversation_id,
        "assistant",
        reply_text,
        metadata={"provider": provider_used, "model": model_used}
    )

    return jsonify({
        "success": True,
        "conversation_id": conversation_id,
        "is_command": False,
        "response": reply_text,
        "provider": provider_used,
        "model": model_used
    })

@app.route("/api/command", methods=["POST"])
def api_command():
    """Explicit endpoint for assistant command execution."""
    data = request.get_json(silent=True) or {}
    command_str = data.get("command", "").strip()
    conversation_id = data.get("conversation_id")

    if not command_str:
        return jsonify({"success": False, "error": "Command string cannot be empty."}), 400

    result = execute_command(command_str, context={"conversation_id": conversation_id})
    return jsonify(result)

# ==========================================================
# VOICE ASSISTANT API ROUTES
# ==========================================================

@app.route("/api/voice/transcribe", methods=["POST"])
def api_voice_transcribe():
    """
    Accept audio recording from client and return transcribed speech text.
    """
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided in request."}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"success": False, "error": "Empty audio file."}), 400

    orig_ext = audio_file.filename.rsplit(".", 1)[-1].lower() if "." in audio_file.filename else "wav"
    safe_name = f"voice_input_{uuid.uuid4().hex[:8]}.{orig_ext}"
    filepath = os.path.join(config.UPLOAD_FOLDER, safe_name)
    audio_file.save(filepath)

    try:
        result = speech_recognition_service.transcribe_file(filepath)
        return jsonify(result)
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

@app.route("/api/voice/speak", methods=["POST"])
def api_voice_speak():
    """
    Accept text and synthesize speech audio file (WAV) via pyttsx3.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "Text is required for speech synthesis."}), 400

    result = text_to_speech_service.synthesize_to_file(text)
    return jsonify(result)

@app.route("/api/voice/interact", methods=["POST"])
def api_voice_interact():
    """
    Full voice interaction loop:
    Accepts audio file OR text query -> Transcribes -> Generates AI response -> Synthesizes Speech.
    """
    conversation_id = request.form.get("conversation_id")
    text_prompt = request.form.get("text")
    temp_audio_path = None

    if "audio" in request.files:
        audio_file = request.files["audio"]
        if audio_file.filename:
            orig_ext = audio_file.filename.rsplit(".", 1)[-1].lower() if "." in audio_file.filename else "wav"
            safe_name = f"voice_turn_{uuid.uuid4().hex[:8]}.{orig_ext}"
            temp_audio_path = os.path.join(config.UPLOAD_FOLDER, safe_name)
            audio_file.save(temp_audio_path)

    try:
        result = voice_service.process_voice_interaction(
            audio_filepath=temp_audio_path,
            text_prompt=text_prompt,
            conversation_id=conversation_id
        )
        return jsonify(result)
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except Exception:
                pass

# ==========================================================
# FILE PROCESSING & UPLOAD ROUTES
# ==========================================================

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Upload and validate user files.
    Saves to uploads folder and returns metadata.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Filename is missing."}), 400

    raw_filename = secure_filename(file.filename)
    if not raw_filename:
        raw_filename = f"upload_{uuid.uuid4().hex[:6]}"

    ext = raw_filename.rsplit(".", 1)[-1].lower() if "." in raw_filename else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": f"File type not supported. Allowed formats: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}"
        }), 400

    # Prefix with uuid to prevent accidental collisions while retaining original name
    unique_name = f"{uuid.uuid4().hex[:6]}_{raw_filename}"
    save_path = os.path.join(config.UPLOAD_FOLDER, unique_name)
    file.save(save_path)

    file_size = os.path.getsize(save_path)
    file_type = "image" if ext in config.ALLOWED_IMAGE_EXTENSIONS else ("pdf" if ext == "pdf" else "document")

    return jsonify({
        "success": True,
        "filename": unique_name,
        "original_name": file.filename,
        "size": file_size,
        "type": file_type,
        "url": f"/download/{unique_name}"
    })

@app.route("/api/pdf/compress", methods=["POST"])
def api_pdf_compress():
    """
    Process PDF compression with iLovePDF REST API.
    """
    filepath = None
    
    # Check if a new file is uploaded directly
    if "file" in request.files:
        f = request.files["file"]
        if f.filename:
            clean_name = secure_filename(f.filename)
            if not clean_name.lower().endswith(".pdf"):
                return jsonify({"success": False, "error": "File must be a valid PDF document."}), 400
            unique_name = f"{uuid.uuid4().hex[:6]}_{clean_name}"
            filepath = os.path.join(config.UPLOAD_FOLDER, unique_name)
            f.save(filepath)

    # Or check if filename in uploads was provided
    if not filepath:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename") or request.form.get("filename")
        if filename:
            safe = secure_filename(filename)
            candidate = os.path.join(config.UPLOAD_FOLDER, safe)
            if os.path.exists(candidate):
                filepath = candidate

    if not filepath or not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Please provide a valid PDF file to compress."}), 400

    result = ilovepdf_client.compress_pdf(filepath)
    return jsonify(result)

@app.route("/api/image/enhance", methods=["POST"])
def api_image_enhance():
    """
    Process image enhancement via Pillow / AI provider.
    """
    filepath = None

    if "file" in request.files:
        f = request.files["file"]
        if f.filename:
            clean_name = secure_filename(f.filename)
            ext = clean_name.rsplit(".", 1)[-1].lower() if "." in clean_name else ""
            if ext not in config.ALLOWED_IMAGE_EXTENSIONS:
                return jsonify({
                    "success": False,
                    "error": f"Invalid image format. Allowed: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
                }), 400
            unique_name = f"{uuid.uuid4().hex[:6]}_{clean_name}"
            filepath = os.path.join(config.UPLOAD_FOLDER, unique_name)
            f.save(filepath)

    if not filepath:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename") or request.form.get("filename")
        if filename:
            safe = secure_filename(filename)
            candidate = os.path.join(config.UPLOAD_FOLDER, safe)
            if os.path.exists(candidate):
                filepath = candidate

    if not filepath or not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Please provide a valid image file to enhance."}), 400

    result = image_enhancement_service.enhance_image(filepath)
    return jsonify(result)

@app.route("/download/<path:filename>")
def download_file(filename: str):
    """
    Safely download or preview an output or uploaded file.
    Strictly protects against path traversal vulnerabilities.
    """
    if not is_safe_filename(filename):
        abort(400, description="Invalid filename format.")

    # Check output folder first
    out_path = os.path.join(config.OUTPUT_FOLDER, filename)
    if os.path.exists(out_path):
        return send_from_directory(config.OUTPUT_FOLDER, filename, as_attachment=False)

    # Check upload folder
    upload_path = os.path.join(config.UPLOAD_FOLDER, filename)
    if os.path.exists(upload_path):
        return send_from_directory(config.UPLOAD_FOLDER, filename, as_attachment=False)

    abort(404, description="File not found.")

# ==========================================================
# CONVERSATION HISTORY API ROUTES
# ==========================================================

@app.route("/api/history", methods=["GET"])
def api_get_conversations():
    """Retrieve all conversations list."""
    convs = get_conversations()
    return jsonify({"success": True, "conversations": convs})

@app.route("/api/history/<conversation_id>", methods=["GET"])
def api_get_single_conversation(conversation_id: str):
    """Retrieve a single conversation and its messages."""
    safe_id = secure_filename(conversation_id)
    conv = get_conversation(safe_id)
    if not conv:
        return jsonify({"success": False, "error": "Conversation not found."}), 404
    return jsonify({"success": True, "conversation": conv})

@app.route("/api/history", methods=["POST"])
def api_create_conversation():
    """Create a new conversation session."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "New Conversation")
    conv_id = create_conversation(title=title)
    return jsonify({"success": True, "id": conv_id, "title": title})

@app.route("/api/history/<conversation_id>", methods=["DELETE"])
def api_delete_conversation(conversation_id: str):
    """Delete a conversation."""
    safe_id = secure_filename(conversation_id)
    success = delete_conversation(safe_id)
    if success:
        return jsonify({"success": True, "deleted_id": safe_id})
    return jsonify({"success": False, "error": "Conversation not found or could not be deleted."}), 404

@app.route("/api/status", methods=["GET"])
def api_status():
    """Status endpoint reporting active AI provider and server health."""
    status = assistant_service.get_provider_status()
    return jsonify({
        "status": "healthy",
        "app_name": "Sara AI",
        "version": "2.0.0",
        "ai_status": status,
        "voice_capabilities": {
            "speech_recognition": speech_recognition_service.is_available(),
            "local_tts": text_to_speech_service.is_available()
        }
    })

# ==========================================================
# APPLICATION ENTRYPOINT
# ==========================================================

if __name__ == "__main__":
    # Run locally on port 5000 (standard Windows 11 local developer server)
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"\n==================================================")
    print(f"  Sara AI — Personal AI Chat & Voice Assistant")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug_mode)
