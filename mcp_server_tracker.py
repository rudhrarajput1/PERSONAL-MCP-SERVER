import os
import time
import json
import logging
from functools import wraps
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKER_LOG_PATH = os.path.join(BASE_DIR, "mcp_activity.log")
CRASH_THRESHOLD = 3  # consecutive failures before logging an alert

logging.basicConfig(filename=TRACKER_LOG_PATH, level=logging.INFO, format="%(message)s")
_tracker_logger = logging.getLogger("mcp_tracker")
_consecutive_failures = defaultdict(int)


def track(func):
    """Decorator: logs each call's duration and outcome; alerts on repeated failures."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        tool_name = func.__name__
        try:
            result = func(*args, **kwargs)
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            _consecutive_failures[tool_name] = 0
            _tracker_logger.info(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "duration_ms": duration_ms,
                "status": "success",
            }))
            return result
        except Exception as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            _consecutive_failures[tool_name] += 1
            _tracker_logger.info(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
            }))
            if _consecutive_failures[tool_name] >= CRASH_THRESHOLD:
                _tracker_logger.warning(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "alert": f"{tool_name} failed {_consecutive_failures[tool_name]}x in a row",
                }))
            raise
    return wrapper
