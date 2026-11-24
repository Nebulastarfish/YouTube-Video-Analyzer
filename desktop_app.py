"""
desktop_app.py - Standalone Desktop Entry Point for YouTube Video Analyzer.

Uses PyWebView to launch a native desktop window wrapping the local
Flask backend. Compiled to a standalone .exe with PyInstaller.

Usage:
    python desktop_app.py
"""

import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import time
import socket
import threading
import webview

from app import run_server


def get_base_dir() -> str:
    """Return the directory containing the .exe (when bundled) or script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def ensure_env_file():
    """Ensure a .env template exists next to the executable if not present."""
    base_dir = get_base_dir()
    env_path = os.path.join(base_dir, ".env")
    if not os.path.exists(env_path):
        template = (
            "# Get your Gemini API key from: https://aistudio.google.com/apikey\n"
            "GEMINI_API_KEY=your_gemini_api_key_here\n"
        )
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(template)
        except Exception:
            pass


def find_free_port(default_port: int = 5000) -> int:
    """Check if the default port is free; if not, find an open port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", default_port)) != 0:
            return default_port
    # Find any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 5.0) -> bool:
    """Wait until the Flask server begins accepting socket connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.05)
    return False


def main():
    # 1. Ensure .env template exists in the app folder
    ensure_env_file()

    # 2. Pick host and port
    host = "127.0.0.1"
    port = find_free_port(5000)
    server_url = f"http://{host}:{port}"

    # 3. Start Flask in a background daemon thread
    server_thread = threading.Thread(
        target=run_server,
        kwargs={"host": host, "port": port, "debug": False},
        daemon=True,
    )
    server_thread.start()

    # 4. Wait briefly for Flask to be ready
    wait_for_server(host, port, timeout=5.0)

    # 5. Create native desktop window
    window = webview.create_window(
        title="🎬 YouTube Video Analyzer",
        url=server_url,
        width=1200,
        height=850,
        min_size=(900, 650),
        text_select=True,
        zoomable=True,
    )

    # 6. Graceful shutdown handler
    def on_closed():
        # Forcefully terminate any background workers/threads when window closes
        os._exit(0)

    window.events.closed += on_closed

    # 7. Start the native GUI loop (blocks until window is closed)
    webview.start(gui="edgechromium", debug=False)

    # 8. Clean exit
    os._exit(0)


if __name__ == "__main__":
    main()
