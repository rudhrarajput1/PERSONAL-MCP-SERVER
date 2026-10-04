"""Personal MCP Server — exposes personal projects as MCP tools."""

import json
import os
from datetime import datetime, timezone
from typing import Optional

import feedparser 
from mcp.server.mcpserver import MCPServer
from mcp_server_tracker import track
import socket

try:
    import ollama
except ImportError:
    ollama = None

try:
    from google import genai as google_genai
except ImportError:
    google_genai = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")

# Config


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKMARKS_PATH = os.path.join(BASE_DIR, "bookmarks.json")

# Category -> RSS feed URL. Swap these for whatever feeds your widget uses.
FEEDS = {
    "AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "ML": "https://www.technologyreview.com/feed/",
    "Tech": "https://techcrunch.com/feed/",
}

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
    feed = feedparser.parse(FEEDS[category])

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
    
    # it saves the news titles and links in the bookmarks.json file in the same directory as this script.
    
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
    
    # List saved news items, optionally filtering by a search query.
    
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
    
    # Un-star a previously saved news item.

    
    bookmarks = _load_bookmarks()
    filtered = [b for b in bookmarks if b["link"] != link]

    if len(filtered) == len(bookmarks):
        return "No matching saved item found."

    _save_bookmarks(filtered)
    return "Removed from saved news."


@mcp.tool()
@track
def list_categories() -> list[str]:
    # List the news categories available (matches the widget's category slider).
    return list(FEEDS.keys())


if __name__ == "__main__":
    mcp.run()



#  the claude or any other ai main preference is google gemini using the ollama as a fatch source and import the data from the local ai when asked
# Tools — Offline AI Fallback (Gemini online, Ollama offline)


def _is_online(host="8.8.8.8", port=53, timeout=2.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def _ask(prompt: str, backend: str) -> str:
    if backend == "gemini":
        client = google_genai.Client(api_key=GEMINI_API_KEY)
        return client.models.generate_content(model=GEMINI_MODEL, contents=prompt).text
    return ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])["message"]["content"]


@mcp.tool()
@track
def check_connectivity() -> dict:
    """Report online status and which backend ai_chat() would use."""
    online = _is_online()
    return {"online": online, "would_use": "gemini" if online and GEMINI_API_KEY else "ollama"}

@mcp.tool()
@track
def ai_chat(prompt: str, force_offline: bool = False) -> dict:
    """Chat via Gemini if online, else fall back to local Ollama."""
    note = None
    if not force_offline and GEMINI_API_KEY and _is_online():
        try:
            return {"backend": "gemini", "response": _ask(prompt, "gemini")}
        except Exception as e:
            note = f"Gemini failed, used Ollama instead: {e}"

    try:
        result = {"backend": "ollama", "response": _ask(prompt, "ollama")}
        if note:
            result["note"] = note
        return result
    except Exception as e:
        return {"backend": "none", "error": str(e)}
    