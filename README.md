# Personal MCP Server

A local MCP server that gives any AI client (Claude Desktop, etc.)
access to my personal tools — currently an AI news widget and an
offline-capable AI chat that can use a configurable OpenAI-compatible
online API and fall back to Ollama or another configured backend.

> **Why:** I wanted AI tools that work in a flight-mode / dead-Wi-Fi
> situation without reconfiguring anything.

## Architecture

```
MCP Client (Claude Desktop)
       │ stdio
       ▼
Personal MCP Server (Python)
 ├── AI News Widget → [news RSS feeds] → bookmarks.json
 └── AI Chat → [Online?] ──▶ Configured OpenAI-compatible API
               └─Offline──▶ Configured local/custom backend
```

## Tech stack

`Python` · `MCP (stdio transport)` · `OpenAI-compatible APIs` · `Ollama` · `feedparser` · `JSON`

## Tools exposed

### AI News
| Tool | What it does |
|---|---|
| `get_latest_news(category, limit)` | Fetch latest headlines for "AI", "ML", or "Tech" |
| `save_news(title, link, source, category)` | Bookmark an article |
| `list_saved_news(query)` | List saved articles, optionally filtered |
| `remove_saved_news(link)` | Remove a bookmark |
| `list_categories()` | List available categories |

### AI Chat (online/offline fallback)
| Tool | What it does |
|---|---|
| `ai_chat(prompt, force_offline)` | Sends a prompt to the configured online API if available, otherwise tries the configured local/custom backend |
| `check_connectivity()` | Reports online status and which backend would currently be used |

## Why these design choices

- **JSON over SQLite for bookmarks**: simplicity — no database
  dependency for what is currently a single-user, low-volume list.
  Would move to SQLite if this needed concurrent access or querying
  at scale.
- **Ollama model**: default is `llama3`, chosen for a reasonable
  speed/quality tradeoff on consumer hardware. Swappable via the
  `OLLAMA_MODEL` environment variable — tested working with Qwen2.5
  and Kimi K2 as drop-in alternatives.
- **stdio transport**: matches how Claude Desktop launches local MCP
  servers as a subprocess — no network port needed for local use.

## Limitations

- Local model quality is noticeably lower than a capable remote online model for complex,
  multi-step reasoning — fine for quick lookups, not a full
  replacement.
- News fetching depends on the upstream RSS feeds staying available
  and unchanged; a dead/unreachable feed returns a clear error object
  instead of failing silently, but there's no retry/backoff logic yet.
- Connectivity check is a best-effort socket probe, not a guarantee that
  the configured online API is reachable or authenticated.

## Setup

```bash
pip install -r requirements.txt
```

**Offline AI fallback:**
- Default OpenAI-compatible backend: install [Ollama](https://ollama.com), pull a model, and set
  `OFFLINE_BACKEND_TYPE=openai` (this is the default).
- Optional variables: `OFFLINE_BASE_URL`, `OFFLINE_MODEL`, or legacy `OLLAMA_MODEL`.
- Set `ONLINE_API_KEY` as an environment variable for the online path (optional).
- Custom backend: set `OFFLINE_BACKEND_TYPE=custom` and
  `OFFLINE_CUSTOM_CMD` to a command that reads the prompt from stdin and prints the answer to stdout.
  Arguments and executable paths containing spaces should be quoted.

## Run it

```bash
python personal_MCP_server.py
```

Runs over stdio and waits for an MCP client to connect — no output
on its own is expected.

## Connect it to Claude Desktop

```json
{
  "mcpServers": {
    "personal-mcp-server": {
      "command": "/full/path/to/venv/Scripts/python.exe",
      "args": ["/full/path/to/personal_mcp_server.py"]
    }
  }
}
```

## License

MIT — see [LICENSE](LICENSE).

## Status

Actively developed — tools are being added as new personal projects
come online. Tests are planned (`pytest`) but not yet written.
