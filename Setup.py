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
    if shutil.which("ollama") is None:
        print(
            "-> Ollama not found on PATH.\n"
            "   Install it from https://ollama.com, then re-run this script.\n"
            "   (Windows: make sure Ollama is installed and the app has been run once\n"
            "   so 'ollama' is registered on PATH — a terminal restart may be needed.)"
        )
        sys.exit(1)

    model = os.environ.get("OLLAMA_MODEL", "llama3")
    print(f"-> Pulling Ollama model: {model}")
    run(["ollama", "pull", model])

    # 3. Gemini key (optional)
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "-> No GEMINI_API_KEY set. The server will run fully offline via Ollama.\n"
            "   To enable the online Gemini path later:\n"
            "     Windows (PowerShell): $env:GEMINI_API_KEY = \"your_key\"\n"
            "     Mac/Linux:             export GEMINI_API_KEY=your_key"
        )
    else:
        print("-> GEMINI_API_KEY detected — online path enabled.")

    print("== Setup complete. Run: python personal_mcp_server.py ==")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Setup step failed: {e}")
        sys.exit(1)