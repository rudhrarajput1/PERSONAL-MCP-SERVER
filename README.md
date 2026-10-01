# Personal MCP Server

A growing MCP server exposing personal projects as callable tools —
currently the **AI News Widget** (fetch AI/ML/Tech headlines,
save/star, search/remove saved news) and an **Offline AI Fallback**
system (auto-switching between Gemini online and a local Ollama
model, so it keeps working without internet).

Any MCP-compatible client (e.g. Claude Desktop) can connect to this
server and use these tools directly.

## Tools

### AI News Widget
| Tool | What it does |
|---|---|
| `get_latest_news(category, limit)` | Fetch latest headlines for "AI", "ML", or "Tech" |
| `save_news(title, link, source, category)` | Star/bookmark an article |
| `list_saved_news(query)` | List saved articles, optionally filtered by title/source |
| `remove_saved_news(link)` | Un-star an article |
| `list_categories()` | List available categories |

### Offline AI Fallback
| Tool | What it does |
|---|---|
| `ai_chat(prompt, force_offline)` | Send a prompt — uses Gemini if online + API key is set, else falls back to a local Ollama model. `force_offline=True` skips Gemini entirely. |
| `check_connectivity()` | Reports whether you're online and which backend would currently be used |

**Privacy note:** the online path (`ai_chat` without `force_offline`)
sends the prompt to Google's Gemini API. For anything that must stay
fully local, call with `force_offline=True`.

## Setup

```bash
pip install -r requirements.txt
```

**Offline AI fallback:**
- Install [Ollama](https://ollama.com) and pull a model, e.g.
  `ollama pull llama3` (or `qwen2.5`, `kimi-k2`, etc. — any model
  available in Ollama's library works).
- For the online path, set an environment variable:
  ```bash
  GEMINI_API_KEY=your-key-here
  ```
  If unset, the server always uses the local Ollama model.
- Optional: set `OLLAMA_MODEL` to use a model other than `llama3`.

## Run it

```bash
python3 "personal MCP server.py"
```

It runs over stdio and waits for an MCP client to connect — no
output on its own is expected.

## Connect it to Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "personal-mcp-server": {
      "command": "/full/path/to/venv/Scripts/python.exe",
      "args": ["/full/path/to/personal MCP server.py"]
    }
  }
}
```

Restart Claude Desktop — the tools above will show up under this
server's name.

## Notes

- `bookmarks.json` stores saved news locally and is gitignored —
  it's user data, not part of the repo.
- Each project's tools live under their own `# Tools — <project>`
  section in the server file, so more personal projects can be
  added cleanly over time.
