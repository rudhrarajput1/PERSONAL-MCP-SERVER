---
name: personal-projects-server
description: Fetches AI/ML/Tech news headlines, bookmarks articles, and provides AI chat through a configurable online OpenAI-compatible API with an optional OpenAI-compatible or custom offline fallback. Use when the user asks for AI/ML/Tech news, wants to save or list bookmarked articles, or needs a chat assistant whose backend can fall back when the online service fails.
license: MIT
compatibility: Requires Python 3.10+. RSS/news and online chat require network access; an available offline backend is optional. The default offline backend expects an OpenAI-compatible local server such as Ollama, while custom backends must read the prompt from stdin and print the response to stdout.
---

# Personal News + Offline AI Fallback

This skill exposes two related tool groups over MCP:

1. **AI News** — fetch, save, list, and remove bookmarked headlines from AI/ML/Tech RSS feeds.
2. **AI Chat (online/offline fallback)** — sends prompts through a configurable OpenAI-compatible
   online API when available, then falls back to the configured offline backend when the online
   backend is disabled or fails.

## When to use this skill

- The user asks for recent AI, ML, or Tech news/headlines.
- The user wants to bookmark, list, or remove saved articles.
- The user wants to chat with an AI assistant and may be offline, or explicitly asks for an
  offline-capable chat.

## Setup (one-time, per user)

An online API key is optional. If provided, the key belongs to the user or deployment and must
not be shared or hardcoded in this repository. The default online endpoint uses Gemini's
OpenAI-compatible API, but `ONLINE_BASE_URL` can point to another compatible provider.

```bash
python setup.py
```

This installs dependencies and, with the default `openai` offline backend, checks for Ollama and
pulls the configured model. An offline backend is not guaranteed by setup: availability depends
on the configured local server or custom command.

To enable the online path:

```
# Windows (PowerShell)
$env:ONLINE_API_KEY = "your_key"

# Mac/Linux
export ONLINE_API_KEY=your_key
```

The online path also supports `ONLINE_BASE_URL`, `ONLINE_MODEL`, and the legacy
`GEMINI_API_KEY` variable. Ollama remains the default offline example, but the server can use
any OpenAI-compatible local endpoint:

```bash
# Windows (PowerShell)
$env:OFFLINE_BACKEND_TYPE = "openai"
$env:OFFLINE_BASE_URL = "http://localhost:11434/v1"
$env:OFFLINE_MODEL = "llama3:8b"

# Windows: custom stdin/stdout command
$env:OFFLINE_BACKEND_TYPE = "custom"
$env:OFFLINE_CUSTOM_CMD = "python C:\path\to\custom_backend.py"
```

## Tools

| Tool | Use when |
|---|---|
| `get_latest_news(category, limit)` | User wants headlines for "AI", "ML", or "Tech" |
| `save_news(title, link, source, category)` | User wants to bookmark an article |
| `list_saved_news(query)` | User wants to see saved articles, optionally filtered |
| `remove_saved_news(link)` | User wants to remove a bookmark |
| `list_categories()` | User asks what news categories are available |
| `ai_chat(prompt, force_offline)` | User wants a chat response; auto-falls back to the configured offline backend |
| `check_connectivity()` | User asks whether they're online, or which backend would be used |

## Notes for the agent

- Do not assume an online API key or offline backend is configured — use
  `check_connectivity()` to determine the backend that would be used.
- A dead/unreachable RSS feed returns `{"error": ...}` instead of an empty list; surface that
  message to the user rather than reporting "no news today."
- - An online API key is optional. Never ask the user to share it or hardcode it anywhere.