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

    
    # 2. Offline backend setup
    has_online_key = bool(os.environ.get("ONLINE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    offline_type = os.environ.get("OFFLINE_BACKEND_TYPE", "openai").strip().lower()

    if offline_type == "custom":
        custom_command = os.environ.get("OFFLINE_CUSTOM_CMD")
        if custom_command:
            print(f"-> Custom offline backend configured: {custom_command}")
        else:
            print(
                "-> OFFLINE_BACKEND_TYPE=custom requires OFFLINE_CUSTOM_CMD.\n"
                "   Set it to a command that reads a prompt from stdin."
            )
            if not has_online_key:
                sys.exit(1)
    elif offline_type == "openai":
        if shutil.which("ollama") is None:
            if has_online_key:
                print(
                    "-> Ollama not found on PATH — skipping offline setup.\n"
                    "   The online path is enabled; install Ollama later for offline fallback."
                )
            else:
                print(
                    "-> Ollama not found on PATH, and no online API key is set either.\n"
                    "   Install Ollama or set ONLINE_API_KEY to use the online path."
                )
                sys.exit(1)
        else:
            model = os.environ.get(
                "OFFLINE_MODEL",
                os.environ.get("OLLAMA_MODEL", "llama3:8b"),
            )
            print(f"-> Pulling Ollama model: {model}")
            run(["ollama", "pull", model])
    else:
        print("-> OFFLINE_BACKEND_TYPE must be 'openai' or 'custom'.")
        if not has_online_key:
            sys.exit(1)
        
        
    # 3. Gemini key (optional)
    if not (os.environ.get("ONLINE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        if offline_type == "custom":
            offline_description = "custom offline backend"
        else:
            offline_description = "Ollama"
        print(
            f"-> No ONLINE_API_KEY set. The server will run fully offline via {offline_description}.\n"
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