"""
Sara AI — Entrypoint redirect to app.py
Allows launching either via `python app.py` or `python main.py`.
"""
import os
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"\n==================================================")
    print(f"  Sara AI — Personal AI Chat & Voice Assistant")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug_mode)
