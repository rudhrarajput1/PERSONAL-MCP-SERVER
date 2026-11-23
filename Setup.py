#!/usr/bin/env python3
"""
One-command setup for Personal MCP Server.
Works on Windows, macOS, and Linux.

Usage:
    python setup.py
"""

import os
import shutil
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print(f"-> Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> None:
    print("== Personal MCP Server setup ==")

    # 1. Python dependencies
    print("-> Installing Python dependencies...")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    
    # 2. Ollama check + model pull (for offline fallback)
    # Only required if the user has no online API key — otherwise offline
    # fallback is optional, so missing Ollama shouldn't block setup.
    has_online_key = bool(os.environ.get("ONLINE_API_KEY") or os.environ.get("GEMINI_API_KEY"))

    if shutil.which("ollama") is None:
        if has_online_key:
            print(
                "-> Ollama not found on PATH — skipping offline setup.\n"
                "   You have an online API key set, so the online path will work fine.\n"
                "   Install Ollama later from https://ollama.com if you want offline fallback too."
            )
        else:
            print(
                "-> Ollama not found on PATH, and no online API key is set either.\n"
                "   At least one backend is required. Either:\n"
                "     - Install Ollama from https://ollama.com, then re-run this script, or\n"
                "     - Set ONLINE_API_KEY to use the online path instead.\n"
                "   (Windows: make sure Ollama is installed and the app has been run once\n"
                "   so 'ollama' is registered on PATH — a terminal restart may be needed.)"
            )
            sys.exit(1)
    else:
        model = os.environ.get("OLLAMA_MODEL", "llama3:8b")
        print(f"-> Pulling Ollama model: {model}")
        run(["ollama", "pull", model])
        
        
    # 3. Gemini key (optional)
    if not (os.environ.get("ONLINE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        print(
            "-> No ONLINE_API_KEY set. The server will run fully offline via Ollama.\n"
            "   To enable the online Gemini path later:\n"
            "     Windows (PowerShell): $env:ONLINE_API_KEY = \"your_key\"\n"
            "     Mac/Linux:             export ONLINE_API_KEY=your_key"
        )
    else:
        print("-> Online API key detected — online path enabled.")

    print("== Setup complete. Run: python personal_mcp_server.py ==")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Setup step failed: {e}")
        sys.exit(1)