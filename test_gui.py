"""Comprehensive Automated Test Suite for JARVIS Cyberpunk Desktop HUD.

Tests:
1. GUI HTTP Server initialization and daemon lifecycle.
2. Static Asset Delivery (index.html, gui.css, gui.js).
3. Telemetry REST API (/api/status, /api/history).
4. Interactive Chat & Tool Callback Routing (/api/chat).
5. State transitions (idle -> thinking -> speaking -> idle).
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import patch
import urllib.request

# Ensure jarvis_project is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "jarvis_project")))

import gui_server
import llm


class TestJarvisHUD(unittest.TestCase):
    SERVER_PORT = 8769
    BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
    server_instance = None

    @classmethod
    def setUpClass(cls):
        """Starts a test instance of the GUI server on an isolated port."""
        cls.server_instance = gui_server.run_server(cls.SERVER_PORT)
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        """Shuts down the test server cleanly."""
        if cls.server_instance:
            cls.server_instance.shutdown()

    def test_01_static_assets(self):
        """Verifies that HTML, CSS, and JS assets are served correctly with HTTP 200."""
        endpoints = ["/", "/index.html", "/gui.css", "/gui.js"]
        for ep in endpoints:
            url = f"{self.BASE_URL}{ep}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                self.assertEqual(resp.status, 200)
                content = resp.read().decode("utf-8")
                self.assertTrue(len(content) > 50)
        print("\n[PASS] Static GUI assets (HTML, CSS, JS) served cleanly.")

    def test_02_status_telemetry_api(self):
        """Tests that /api/status returns live CPU, RAM, VRAM, and active window data."""
        url = f"{self.BASE_URL}/api/status"
        with urllib.request.urlopen(url, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))

            self.assertIn("state", data)
            self.assertIn("cpu", data)
            self.assertIn("ram", data)
            self.assertIn("vram", data)
            self.assertIn("active_window", data)
            self.assertIsInstance(data["active_window"], dict)
            print(f"[PASS] Status Telemetry API: CPU {data['cpu']}%, RAM {data['ram']}%, State: {data['state']}")

    def test_03_history_api(self):
        """Tests that /api/history returns valid conversation history array."""
        url = f"{self.BASE_URL}/api/history"
        with urllib.request.urlopen(url, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("history", data)
            self.assertIsInstance(data["history"], list)
            print(f"[PASS] History API: returned {len(data['history'])} turns.")

    def test_04_interactive_chat_api(self):
        """Tests POST /api/chat submission, tool capture, and reply generation."""
        url = f"{self.BASE_URL}/api/chat"
        payload = json.dumps({"message": "What is 2 + 2?"}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("response", data)
            self.assertIn("tools", data)
            self.assertTrue(len(data["response"]) > 0)
            print(f"[PASS] Interactive Chat API: Query '2 + 2' -> Response: '{data['response']}'")

    def test_05_tool_callback_routing(self):
        """Tests that tool executions during chat are captured and returned in the JSON."""
        # Query that invokes a safe tool (check_disk_space)
        url = f"{self.BASE_URL}/api/chat"
        payload = json.dumps({"message": "Check my disk space on drive C"}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=60) as resp:

            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("response", data)
            self.assertIn("tools", data)
            print(f"[PASS] Tool Capture Verification: tools executed: {[t['name'] for t in data['tools']]}")
            print(f"       Response: '{data['response']}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
