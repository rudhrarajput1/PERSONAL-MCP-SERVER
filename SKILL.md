---
name: personal-projects-server 
description: Fetches AI/ML/Tech news headlines, bookmarks articles, and provides an AI chat that automatically falls back from Gemini (online) to a local Ollama model (offline). Use when the user asks for AI/ML/Tech news, wants to save or list bookmarked articles, or needs a chat assistant that keeps working without internet.
license: MIT
compatibility: Requires Python 3.10+, network access for Gemini/RSS, and a locally running Ollama instance for offline chat.
---

# Personal News + Offline AI Fallback

This skill exposes two related tool groups over MCP:

1. **AI News** — fetch, save, list, and remove bookmarked headlines from AI/ML/Tech RSS feeds.
2. **AI Chat (online/offline fallback)** — sends prompts to Gemini when online; automatically
   falls back to a local Ollama model when offline or when Gemini fails.

## When to use this skill

- The user asks for recent AI, ML, or Tech news/headlines.
- The user wants to bookmark, list, or remove saved articles.
- The user wants to chat with an AI assistant and may be offline, or explicitly asks for an
  offline-capable chat.

## Setup (one-time, per user)

Each user must provide their **own** Gemini API key — this skill never ships with a shared key.

```bash
python setup.py
```

This installs dependencies, checks for Ollama, and pulls the configured model. If no
`ONLINE_API_KEY` is set, the skill runs fully offline via Ollama with no additional setup.

To enable the online path:

```
# Windows (PowerShell)
$env:ONLINE_API_KEY = "your_key"

# Mac/Linux
export ONLINE_API_KEY=your_key
```

## Tools

| Tool | Use when |
|---|---|
| `get_latest_news(category, limit)` | User wants headlines for "AI", "ML", or "Tech" |
| `save_news(title, link, source, category)` | User wants to bookmark an article |
| `list_saved_news(query)` | User wants to see saved articles, optionally filtered |
| `remove_saved_news(link)` | User wants to remove a bookmark |
| `list_categories()` | User asks what news categories are available |
| `ai_chat(prompt, force_offline)` | User wants a chat response; auto-falls back to Ollama if offline or Gemini fails |
| `check_connectivity()` | User asks whether they're online, or which backend would be used |

## Notes for the agent

- Do not assume Gemini is configured — always check `check_connectivity()` first if unsure.
- A dead/unreachable RSS feed returns `{"error": ...}` instead of an empty list; surface that
  message to the user rather than reporting "no news today."
- This skill requires the user's own API key for the online path; never ask the user to share
  it with anyone else or hardcode it anywhere.