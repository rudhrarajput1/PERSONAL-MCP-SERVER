"""Personal MCP Server — exposes personal projects as MCP tools."""

import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Optional

import feedparser 
from mcp.server.mcpserver import MCPServer
from mcp_server_tracker import track
import socket

import urllib.request
import urllib.error


# Online backend — any OpenAI-compatible API (OpenAI, Gemini's compatible
# endpoint, Groq, together.ai, etc.). Leave ONLINE_API_KEY unset to disable
# the online path entirely and run fully offline.
ONLINE_BASE_URL = os.environ.get("ONLINE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
ONLINE_API_KEY = os.environ.get("ONLINE_API_KEY") or os.environ.get("GEMINI_API_KEY")
ONLINE_MODEL = os.environ.get("ONLINE_MODEL", "gemini-2.0-flash")

# Offline backend — any OpenAI-compatible local server (Ollama, LM Studio,
# llama.cpp server, or a custom self-hosted model).
OFFLINE_BASE_URL = os.environ.get("OFFLINE_BASE_URL", "http://localhost:11434/v1")
OFFLINE_MODEL = os.environ.get("OFFLINE_MODEL", "llama3:8b")
OFFLINE_BACKEND_TYPE = os.environ.get("OFFLINE_BACKEND_TYPE", "openai").strip().lower()
OFFLINE_CUSTOM_CMD = os.environ.get("OFFLINE_CUSTOM_CMD")


# Config


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKMARKS_PATH = os.path.join(BASE_DIR, "bookmarks.json")

# Category -> RSS feed URL. Swap these for whatever feeds your widget uses.
FEEDS = {
    "AI": "https://research.google/blog/rss/",
    "ML": "https://www.technologyreview.com/feed/",
    "Tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
}
FEED_REQUEST_HEADERS = {"User-Agent": "PersonalMCPServer/1.0"}

mcp = MCPServer("personal-MCP-SERVER")

 

# Bookmark storage helpers


def _load_bookmarks() -> list[dict]:
    if not os.path.exists(BOOKMARKS_PATH):
        return []
    try:
        with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_bookmarks(bookmarks: list[dict]) -> None:
    with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, indent=2)



# Tools — AI News Widget

# (Future tool groups, e.g. Ollama fallback, get their own section
# header below this one so the file stays organized as it grows.)

@mcp.tool()
@track
def get_latest_news(category: str = "AI", limit: int = 10) -> list[dict]:
    """
    Fetch the latest headlines for a category.
    
    Args:
        category: One of "AI", "ML", "Tech" (matches the widget's category slider).
        limit: Max number of headlines to return (default 10).
    """
    category = category if category in FEEDS else "AI"
    feed = feedparser.parse(
        FEEDS[category],
        request_headers=FEED_REQUEST_HEADERS,
    )
    
    if feed.bozo and not feed.entries:
     reason = getattr(feed, "bozo_exception", "unknown error")
     return [{
        "error": f"Could not fetch {category} feed: {reason}",
        "category": category,
    }]

    results = []
    for entry in feed.entries[:limit]:
        results.append({
            "title": entry.get("title", "Untitled"),
            "link": entry.get("link", ""),
            "source": feed.feed.get("title", category),
            "published": entry.get("published", ""),
            "category": category,
        })
    return results


@mcp.tool()
@track
def save_news(title: str, link: str, source: str = "", category: str = "AI") -> str:
    
    """
    Save a news item to bookmarks.json in this script's directory.

    Args:
        title: Headline text.
        link: Article URL — used as the unique key to detect duplicates.
        source: Feed/publication name (e.g. "TechCrunch").
        category: One of "AI", "ML", "Tech".
    """ 

    bookmarks = _load_bookmarks()

    if any(b["link"] == link for b in bookmarks):
        return f"Already saved: {title}"

    bookmarks.append({
        "title": title,
        "link": link,
        "source": source,
        "category": category,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_bookmarks(bookmarks)
    return f"Saved: {title}"


@mcp.tool()
@track
def list_saved_news(query: Optional[str] = None) -> list[dict]:
   """
    List saved news items, optionally filtering by a search query.

    Args:
        query: Case-insensitive substring matched against title or source.
               Omit to return every saved item.
    """
    
   bookmarks = _load_bookmarks()
   if not query:
        return bookmarks

   q = query.lower()
   return [
        b for b in bookmarks
        if q in b["title"].lower() or q in b.get("source", "").lower()
    ]


@mcp.tool()
@track
def remove_saved_news(link: str) -> str:
    
   """
    Un-star a previously saved news item.

    Args:
        link: The exact URL of the saved item to remove.
    """

    
   bookmarks = _load_bookmarks()
   filtered = [b for b in bookmarks if b["link"] != link]

   if len(filtered) == len(bookmarks):
        return "No matching saved item found."

   _save_bookmarks(filtered)
   return "Removed from saved news."


@mcp.tool()
@track
def list_categories() -> list[str]:
    """
    List the news categories available (matches the widget's category slider).
    """
    return list(FEEDS.keys())


# Tools — Online/Offline AI Fallback (any OpenAI-compatible backend)


def _is_online(host="8.8.8.8", port=53, timeout=2.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def _call_openai_compatible(base_url: str, model: str, prompt: str, api_key: Optional[str] = None) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _ask(prompt: str, backend: str) -> str:
    if backend == "online":
        return _call_openai_compatible(ONLINE_BASE_URL, ONLINE_MODEL, prompt, api_key=ONLINE_API_KEY)
    if OFFLINE_BACKEND_TYPE == "custom":
        return _call_custom(OFFLINE_CUSTOM_CMD, prompt)
    return _call_openai_compatible(OFFLINE_BASE_URL, OFFLINE_MODEL, prompt)


def _call_custom(command: Optional[str], prompt: str) -> str:
    if not command:
        raise RuntimeError(
            "OFFLINE_BACKEND_TYPE=custom requires OFFLINE_CUSTOM_CMD"
        )

    try:
        argv = shlex.split(command, posix=(os.name != "nt"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid OFFLINE_CUSTOM_CMD: {exc}") from exc
    if not argv:
        raise RuntimeError("OFFLINE_CUSTOM_CMD is empty")

    executable = argv[0]
    if shutil.which(executable) is None:
        raise RuntimeError(f"Custom backend executable not found: {executable}")

    try:
        result = subprocess.run(
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Custom backend timed out after 30 seconds") from exc

    if result.returncode != 0:
        error = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Custom backend failed: {error}")

    response = result.stdout.strip()
    if not response:
        raise RuntimeError("Custom backend returned no response")
    return response


def _offline_available() -> bool:
    if OFFLINE_BACKEND_TYPE == "custom":
        if not OFFLINE_CUSTOM_CMD:
            return False
        try:
            argv = shlex.split(
                OFFLINE_CUSTOM_CMD,
                posix=(os.name != "nt"),
            )
        except ValueError:
            return False
        return bool(argv) and shutil.which(argv[0]) is not None

    if OFFLINE_BACKEND_TYPE != "openai":
        return False

    try:
        req = urllib.request.Request(OFFLINE_BASE_URL.rstrip("/") + "/models", method="GET")
        urllib.request.urlopen(req, timeout=2)
        return True
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


@mcp.tool()
@track
def check_connectivity() -> dict:
    """Report online status and which backend ai_chat() would use."""
    online = _is_online()
    if online and ONLINE_API_KEY:
        would_use = "online"
    elif OFFLINE_BACKEND_TYPE == "custom":
        would_use = "custom" if _offline_available() else "none"
    elif OFFLINE_BACKEND_TYPE == "openai" and _offline_available():
        would_use = "offline"
    else:
        would_use = "none"
    return {
        "online": online,
        "would_use": would_use,
        "offline_backend_type": OFFLINE_BACKEND_TYPE,
    }


@mcp.tool()
@track
def ai_chat(prompt: str, force_offline: bool = False) -> dict:
    """Chat via the online backend if available, else fall back to the local offline backend."""
    note = None
    if OFFLINE_BACKEND_TYPE not in {"openai", "custom"}:
        return {
            "backend": "none",
            "error": "OFFLINE_BACKEND_TYPE must be 'openai' or 'custom'",
        }

    if not force_offline and ONLINE_API_KEY and _is_online():
        try:
            return {"backend": "online", "response": _ask(prompt, "online")}
        except Exception as e:
            note = f"Online backend failed, falling back to offline: {e}"

    try:
        backend_name = "custom" if OFFLINE_BACKEND_TYPE == "custom" else "offline"
        result = {"backend": backend_name, "response": _ask(prompt, "offline")}
        if note:
            result["note"] = note
        return result
    except Exception as e:
        return {"backend": "none", "error": str(e)}


if __name__ == "__main__":
    mcp.run()