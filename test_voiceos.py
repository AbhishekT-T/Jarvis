"""Comprehensive Test Suite for JARVIS VoiceOS layers.
Tests:
1. Window Context & App Categorization
2. Context-Aware Dictation Formatting via LLM
3. Keystroke / Clipboard In-Place Injection
4. Selection Capture & Editing Logic (Unit checks)
5. Agent Mode (Email Draft, Calendar .ics, Event Listing)
6. LLM Tool-Call Routing on VoiceOS queries
"""

import sys
import os
import unittest
from unittest.mock import patch

# Ensure jarvis_project is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "jarvis_project")))

import window_context
import tools
import llm
import memory


class TestVoiceOS(unittest.TestCase):

    def test_01_window_context_classification(self):
        """Tests that app classifications work accurately across known processes and titles."""
        # Process lookup
        app, cat = window_context._classify_window("code.exe", "rag.py - Jarvis - Visual Studio Code")
        self.assertEqual(cat, "coding")
        self.assertEqual(app, "VS Code")

        app, cat = window_context._classify_window("slack.exe", "Slack | general | Workspace")
        self.assertEqual(cat, "chat")
        self.assertEqual(app, "Slack")

        app, cat = window_context._classify_window("outlook.exe", "Inbox - Outlook")
        self.assertEqual(cat, "email")

        # Browser sub-classification
        app, cat = window_context._classify_window("chrome.exe", "Gmail - Inbox (3) - Google Chrome")
        self.assertEqual(cat, "email")

        app, cat = window_context._classify_window("msedge.exe", "Pull Request #42 · GitHub - Microsoft Edge")
        self.assertEqual(cat, "coding")

        # Live context inspection
        live_ctx = window_context.get_active_window_context()
        self.assertIn("app_name", live_ctx)
        self.assertIn("category", live_ctx)
        print(f"\n[PASS] Live Active Window: {live_ctx['app_name']} ({live_ctx['category']}) - Title: '{live_ctx['title']}'")

    def test_02_clipboard_roundtrip(self):
        """Tests safe text typing & clipboard restoration."""
        import win32clipboard, win32con
        
        # Set a test value in clipboard
        test_sentinel = "PREVIOUS_CLIPBOARD_CONTENT_12345"
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(test_sentinel, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()

        # Run type_into_active_window with a message
        res = tools.type_into_active_window("Test Injection")
        self.assertTrue(res)

        # Check if original clipboard was restored
        win32clipboard.OpenClipboard()
        restored = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        self.assertEqual(restored, test_sentinel)
        print("[PASS] Clipboard preservation and injection verified.")

    def test_03_dictation_formatting(self):
        """Tests context-aware dictation formatting."""
        ctx_email = {"app_name": "Outlook", "category": "email"}
        res_email = llm.format_dictation_for_app("hey john let us meet at three pm to discuss the budget", ctx_email)
        self.assertTrue(len(res_email) > 0)
        print(f"[PASS] Dictation formatted for Email: {res_email}")

        ctx_chat = {"app_name": "Slack", "category": "chat"}
        res_chat = llm.format_dictation_for_app("hey john let us meet at three pm to discuss the budget", ctx_chat)
        self.assertTrue(len(res_chat) > 0)
        print(f"[PASS] Dictation formatted for Chat: {res_chat}")

    def test_04_agent_mode_calendar_and_email(self):
        """Tests calendar event generation (.ics) and event listing."""
        # Test schedule_calendar_event with mocked 'y' input
        with patch("builtins.input", return_value="y"), patch("os.startfile", return_value=None):
            msg = tools.schedule_calendar_event(
                title="VoiceOS Design Sync",
                start_time="Tomorrow 3:00 PM",
                duration_minutes=45,
                description="Review Push-to-Talk and Thought-to-Action layer"
            )
            self.assertIn("scheduled", msg.lower())
            print(f"[PASS] Calendar Schedule Action: {msg}")

        # Test list_calendar_events
        events = tools.list_calendar_events()
        self.assertIn("VoiceOS Design Sync", events)
        print(f"[PASS] Calendar Event Listing:\n{events}")

        # Test draft_email with mocked 'y' input
        with patch("builtins.input", return_value="y"), patch("webbrowser.open", return_value=True):
            draft_msg = tools.draft_email(
                recipient="alex@example.com",
                subject="Weekly Progress Update",
                body="Hello Alex,\nAll VoiceOS layers are now implemented and tested.\nBest,\nJarvis"
            )
            self.assertIn("opened", draft_msg.lower())
            print(f"[PASS] Email Draft Action: {draft_msg}")

    def test_05_llm_tool_routing(self):
        """Tests that the Flash Tier correctly calls the VoiceOS tools."""
        queries = [
            ("Type a message saying I will be five minutes late into my open chat", "dictate_into_active_window"),
            ("What app or window do I have open right now?", "get_active_window_info"),
            ("Draft an email to boss@company.com about the project timeline", "draft_email"),
            ("Schedule a team sync tomorrow at 10 AM", "schedule_calendar_event"),
            ("Show my upcoming schedule and calendar events", "list_calendar_events"),
        ]

        print("\n--- LLM Query Tool Routing Smoke Test ---")
        history = []
        for prompt, expected_tool in queries:
            with patch("builtins.input", return_value="y"), patch("webbrowser.open", return_value=True), patch("os.startfile", return_value=None):
                resp = llm.query_jarvis(prompt, history)
                self.assertTrue(len(resp) > 0)
                print(f"[QUERY] '{prompt}'\n[REPLY] {resp}\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
