#!/usr/bin/env python3
"""Unit tests to verify Google Sheets logging format and fallbacks."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import config
from tools.sheets import log_publication


class TestSheetsLogging(unittest.TestCase):

    def setUp(self) -> None:
        # Save original config values
        self.original_webhook_url = config.SHEET_WEBHOOK_URL

    def tearDown(self) -> None:
        # Restore original config values
        config.SHEET_WEBHOOK_URL = self.original_webhook_url

    def test_log_publication_skipped_when_url_unset(self) -> None:
        """Verify logging is skipped cleanly when SHEET_WEBHOOK_URL is empty."""
        config.SHEET_WEBHOOK_URL = ""
        
        briefing = {
            "headline": "Test Headline",
            "fb_post": "Test Summary Content",
            "story": {
                "url": "https://example.com/news/123",
                "headline_th": "Test Headline TH",
                "summary_th": "Test Summary TH",
                "category": "นโยบาย"
            }
        }
        
        # This should execute and return without throwing any errors or calling requests
        with patch("requests.post") as mock_post:
            log_publication(briefing, card="output/card.png")
            mock_post.assert_not_called()

    def test_log_publication_payload_structure(self) -> None:
        """Verify the payload sent to SHEET_WEBHOOK_URL has the correct Thai/English columns."""
        config.SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/dummy/exec"
        
        briefing = {
            "headline": "พาดหัวสั้นกระชับ",
            "fb_post": "เนื้อความสรุปโพสต์เฟซบุ๊กที่น่าสนใจ",
            "story": {
                "url": "https://alcoholnews.org/some-story",
                "headline_th": "พาดหัวข่าวสรุปไทย",
                "summary_th": "เนื้อความสรุปสั้นๆ",
                "category": "สังคม",
                "kind": "news"
            },
            "region": "thai",
            "editor_note": "บรรณาธิการชอบชิ้นนี้มาก"
        }
        card_path = "output/card-20260621.png"
        
        with patch("requests.post") as mock_post:
            # Mock a successful response
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            log_publication(briefing, card=card_path, express_url="https://express.adobe.com/edit/123")
            
            # Assert requests.post was called
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            # Extract arguments passed to requests.post
            post_url = call_args[0][0]
            post_kwargs = call_args[1]
            
            self.assertEqual(post_url, config.SHEET_WEBHOOK_URL)
            self.assertIn("json", post_kwargs)
            
            payload = post_kwargs["json"]
            self.assertIn("columns", payload)
            self.assertIn("row", payload)
            
            cols = payload["columns"]
            row = payload["row"]
            
            # Check for requested Thai columns
            self.assertIn("Title", cols)
            self.assertIn("วันที่", cols)
            self.assertIn("เนื้อหาข่าวที่สรุป", cols)
            self.assertIn("ที่มาของข้อมูล", cols)
            self.assertIn("รูปปก", cols)
            
            # Verify values inside the row data
            self.assertEqual(row["Title"], "พาดหัวสั้นกระชับ")
            self.assertEqual(row["เนื้อหาข่าวที่สรุป"], "เนื้อความสรุปโพสต์เฟซบุ๊กที่น่าสนใจ")
            self.assertEqual(row["ที่มาของข้อมูล"], "https://alcoholnews.org/some-story")
            self.assertEqual(row["รูปปก"], card_path)
            self.assertEqual(row["category"], "สังคม")
            self.assertEqual(row["region"], "thai")


if __name__ == "__main__":
    unittest.main()
