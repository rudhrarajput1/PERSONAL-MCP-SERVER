import io
import json
import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import personal_MCP_server as server
import setup


class BookmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bookmarks_path = os.path.join(self.temp_dir.name, "bookmarks.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_list_filter_and_remove(self):
        with patch.object(server, "BOOKMARKS_PATH", self.bookmarks_path):
            self.assertEqual(
                server.save_news("Example", "https://example.com", "Example Source", "AI"),
                "Saved: Example",
            )
            self.assertEqual(
                server.save_news("Example", "https://example.com", "Example Source", "AI"),
                "Already saved: Example",
            )

            with open(self.bookmarks_path, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertEqual(len(saved), 1)
            self.assertEqual(server.list_saved_news("example")[0]["link"], "https://example.com")
            self.assertEqual(server.remove_saved_news("https://example.com"), "Removed from saved news.")
            self.assertEqual(server.list_saved_news(), [])

    def test_missing_or_invalid_bookmarks_return_empty(self):
        with patch.object(server, "BOOKMARKS_PATH", os.path.join(self.temp_dir.name, "missing.json")):
            self.assertEqual(server._load_bookmarks(), [])

        invalid_path = os.path.join(self.temp_dir.name, "invalid.json")
        with open(invalid_path, "w", encoding="utf-8") as handle:
            handle.write("{invalid")
        with patch.object(server, "BOOKMARKS_PATH", invalid_path):
            self.assertEqual(server._load_bookmarks(), [])


class NewsTests(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(server.list_categories(), ["AI", "ML", "Tech"])

    def test_latest_news_success(self):
        feed = SimpleNamespace(
            bozo=False,
            entries=[
                {
                    "title": "Test headline",
                    "link": "https://example.com/story",
                    "published": "2026-11-28",
                }
            ],
            feed={"title": "Test Feed"},
        )
        with patch.object(server.feedparser, "parse", return_value=feed) as parse_feed:
            result = server.get_latest_news("AI", 10)

        self.assertEqual(result[0]["title"], "Test headline")
        self.assertEqual(result[0]["source"], "Test Feed")
        self.assertEqual(result[0]["category"], "AI")
        parse_feed.assert_called_once_with(
            server.FEEDS["AI"],
            request_headers={"User-Agent": "PersonalMCPServer/1.0"},
        )

    def test_feed_failure_returns_error_object(self):
        feed = SimpleNamespace(
            bozo=True,
            bozo_exception=ValueError("feed unavailable"),
            entries=[],
        )
        with patch.object(server.feedparser, "parse", return_value=feed):
            result = server.get_latest_news("ML", 10)

        self.assertEqual(len(result), 1)
        self.assertIn("Could not fetch ML feed", result[0]["error"])


class OpenAICompatibleTests(unittest.TestCase):
    def test_openai_request_includes_model_prompt_and_auth(self):
        response = io.BytesIO(
            json.dumps(
                {"choices": [{"message": {"content": "Hello"}}]}
            ).encode("utf-8")
        )
        with patch.object(server.urllib.request, "urlopen", return_value=response) as urlopen:
            result = server._call_openai_compatible(
                "https://example.com/v1",
                "test-model",
                "Hello",
                api_key="secret",
            )

        self.assertEqual(result, "Hello")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"][0]["content"], "Hello")

    def test_online_success_does_not_use_offline_backend(self):
        with (
            patch.object(server, "ONLINE_API_KEY", "secret"),
            patch.object(server, "_is_online", return_value=True),
            patch.object(server, "_ask", return_value="Online answer") as ask,
        ):
            result = server.ai_chat("Hello")

        self.assertEqual(result, {"backend": "online", "response": "Online answer"})
        ask.assert_called_once_with("Hello", "online")

    def test_online_failure_falls_back_to_offline(self):
        def ask(prompt, backend):
            if backend == "online":
                raise RuntimeError("online unavailable")
            return "Offline answer"

        with (
            patch.object(server, "ONLINE_API_KEY", "secret"),
            patch.object(server, "OFFLINE_BACKEND_TYPE", "openai"),
            patch.object(server, "_is_online", return_value=True),
            patch.object(server, "_ask", side_effect=ask),
        ):
            result = server.ai_chat("Hello")

        self.assertEqual(result["backend"], "offline")
        self.assertEqual(result["response"], "Offline answer")
        self.assertIn("falling back to offline", result["note"])

    def test_force_offline_skips_online_backend(self):
        with (
            patch.object(server, "ONLINE_API_KEY", "secret"),
            patch.object(server, "OFFLINE_BACKEND_TYPE", "openai"),
            patch.object(server, "_is_online", return_value=True),
            patch.object(server, "_ask", return_value="Offline answer") as ask,
        ):
            result = server.ai_chat("Hello", force_offline=True)

        self.assertEqual(result, {"backend": "offline", "response": "Offline answer"})
        ask.assert_called_once_with("Hello", "offline")

    def test_invalid_offline_backend_returns_error(self):
        with patch.object(server, "OFFLINE_BACKEND_TYPE", "invalid"):
            result = server.ai_chat("Hello")

        self.assertEqual(result["backend"], "none")
        self.assertIn("must be 'openai' or 'custom'", result["error"])


class CustomBackendTests(unittest.TestCase):
    def test_custom_backend_receives_stdin_and_returns_stdout(self):
        completed = subprocess.CompletedProcess(
            args=["python", "backend.py"],
            returncode=0,
            stdout="Custom answer\n",
            stderr="",
        )
        with (
            patch.object(server.shutil, "which", return_value="/bin/python"),
            patch.object(server.subprocess, "run", return_value=completed) as run,
        ):
            result = server._call_custom("python backend.py", "Hello")

        self.assertEqual(result, "Custom answer")
        args = run.call_args
        self.assertEqual(args.kwargs["input"], "Hello")

    def test_custom_backend_missing_command_returns_error(self):
        with patch.object(server, "OFFLINE_CUSTOM_CMD", None):
            with self.assertRaisesRegex(RuntimeError, "requires OFFLINE_CUSTOM_CMD"):
                server._call_custom(None, "Hello")

    def test_custom_backend_nonzero_exit_returns_error(self):
        completed = subprocess.CompletedProcess(
            args=["python", "backend.py"],
            returncode=1,
            stdout="",
            stderr="backend crashed",
        )
        with (
            patch.object(server.shutil, "which", return_value="/bin/python"),
            patch.object(server.subprocess, "run", return_value=completed),
        ):
            with self.assertRaisesRegex(RuntimeError, "backend crashed"):
                server._call_custom("python backend.py", "Hello")


class ConnectivityTests(unittest.TestCase):
    def test_connectivity_reports_online_backend(self):
        with (
            patch.object(server, "_is_online", return_value=True),
            patch.object(server, "ONLINE_API_KEY", "secret"),
            patch.object(server, "OFFLINE_BACKEND_TYPE", "openai"),
        ):
            result = server.check_connectivity()

        self.assertEqual(result["would_use"], "online")

    def test_connectivity_reports_custom_backend(self):
        with (
            patch.object(server, "_is_online", return_value=False),
            patch.object(server, "OFFLINE_BACKEND_TYPE", "custom"),
            patch.object(server, "OFFLINE_CUSTOM_CMD", "python backend.py"),
            patch.object(server.shutil, "which", return_value="/bin/python"),
        ):
            result = server.check_connectivity()

        self.assertEqual(result["would_use"], "custom")
        self.assertEqual(result["offline_backend_type"], "custom")

    def test_connectivity_reports_offline_backend(self):
        with (
            patch.object(server, "_is_online", return_value=False),
            patch.object(server, "OFFLINE_BACKEND_TYPE", "openai"),
            patch.object(server, "_offline_available", return_value=True),
        ):
            result = server.check_connectivity()

        self.assertEqual(result["would_use"], "offline")


class SetupTests(unittest.TestCase):
    def test_custom_backend_does_not_require_ollama(self):
        env = {
            "OFFLINE_BACKEND_TYPE": "custom",
            "OFFLINE_CUSTOM_CMD": "python backend.py",
            "ONLINE_API_KEY": "secret",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(setup, "run") as run,
            patch.object(setup.shutil, "which") as which,
        ):
            setup.main()

        run.assert_called_once_with(
            [setup.sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        which.assert_not_called()

    def test_custom_backend_missing_command_exits_without_online_key(self):
        env = {"OFFLINE_BACKEND_TYPE": "custom"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(setup, "run"),
            self.assertRaises(SystemExit),
        ):
            setup.main()

    def test_invalid_offline_backend_exits_without_online_key(self):
        env = {"OFFLINE_BACKEND_TYPE": "invalid"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(setup, "run"),
            self.assertRaises(SystemExit),
        ):
            setup.main()

    def test_openai_backend_pulls_configured_model(self):
        env = {
            "OFFLINE_BACKEND_TYPE": "openai",
            "OFFLINE_MODEL": "test-model",
            "ONLINE_API_KEY": "secret",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(setup, "run") as run,
            patch.object(setup.shutil, "which", return_value="/bin/ollama"),
        ):
            setup.main()

        run.assert_any_call(["ollama", "pull", "test-model"])


if __name__ == "__main__":
    unittest.main()
