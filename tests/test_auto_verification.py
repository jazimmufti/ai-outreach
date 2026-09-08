"""Unit and Integration Tests for Automatic Contribution Verification via YouTube Video Description.

Tests all required rules, edge cases, and API integration:
1. Direct match: 'Contributors: @ummer.04' -> AUTO VERIFIED
2. Multiple accounts with match: 'Contributors: @john_doe @ummer.04 @alex123' -> AUTO VERIFIED
3. No match: 'Contributors: @john_doe @alex123' -> FALLBACK
4. No Instagram account: 'Thanks to everyone who worked on this.' -> FALLBACK
5. Instagram URL: 'https://instagram.com/ummer.04' -> AUTO VERIFIED
6. Case differences: '@UMMER.04' -> AUTO VERIFIED
7. Edge cases: punctuation, query params, trailing slashes, empty descriptions, redirects
8. Full API integration with /api/outreach/discover
"""

import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import OutreachStage, RawCreatorResearchResult
from app.services.linked_account import (
    get_linked_instagram_account,
    set_dummy_linked_instagram_account,
    reset_dummy_linked_instagram_account,
    normalize_instagram_username
)
from app.services.youtube_description_parser import (
    extract_instagram_accounts,
    clean_and_normalize_username
)
from app.services.auto_verification import verify_contribution_from_description
from app.services.session_manager import clear_all_sessions, get_session


class TestYouTubeDescriptionParser(unittest.TestCase):
    """Tests for extracting and normalizing Instagram accounts from description text."""

    def test_direct_at_mention(self):
        desc = "Contributors: @ummer.04"
        accounts = extract_instagram_accounts(desc)
        self.assertIn("ummer.04", accounts)

    def test_multiple_accounts(self):
        desc = "Contributors: @john_doe @ummer.04 @alex123"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, ["john_doe", "ummer.04", "alex123"])

    def test_instagram_urls(self):
        # Test standard URL
        desc1 = "Follow: https://instagram.com/ummer.04"
        self.assertEqual(extract_instagram_accounts(desc1), ["ummer.04"])

        # Test URL with www and trailing slash
        desc2 = "Check profile: https://www.instagram.com/ummer.04/"
        self.assertEqual(extract_instagram_accounts(desc2), ["ummer.04"])

        # Test URL with query parameters
        desc3 = "Link: https://instagram.com/ummer.04/?igsh=xyz123"
        self.assertEqual(extract_instagram_accounts(desc3), ["ummer.04"])

        # Test instagr.am shortlink
        desc4 = "Insta: http://instagr.am/ummer.04"
        self.assertEqual(extract_instagram_accounts(desc4), ["ummer.04"])

    def test_case_insensitivity_normalization(self):
        desc = "Editor: @UMMER.04, Thumbnail: @John_Doe"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, ["ummer.04", "john_doe"])

    def test_prefixed_mentions_without_at(self):
        desc = "Instagram: ummer.04\nIG - john_doe"
        accounts = extract_instagram_accounts(desc)
        self.assertIn("ummer.04", accounts)
        self.assertIn("john_doe", accounts)

    def test_punctuation_and_surrounding_text(self):
        desc = "Huge thanks to our editor (@ummer.04!), VFX (@alex123), and audio (@john_doe)."
        accounts = extract_instagram_accounts(desc)
        self.assertIn("ummer.04", accounts)
        self.assertIn("alex123", accounts)
        self.assertIn("john_doe", accounts)

    def test_youtube_redirect_unwrapping(self):
        desc = "Instagram: https://www.youtube.com/redirect?q=https%3A%2F%2Finstagram.com%2Fummer.04"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, ["ummer.04"])

    def test_no_instagram_accounts(self):
        desc = "Thanks to everyone who worked on this project. Subscribe for more videos!"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, [])

    def test_empty_and_none_description(self):
        self.assertEqual(extract_instagram_accounts(""), [])
        self.assertEqual(extract_instagram_accounts(None), [])
        self.assertEqual(extract_instagram_accounts("    \n\t  "), [])

    def test_deduplication(self):
        desc = "@ummer.04 collaborated on this. Follow https://instagram.com/ummer.04 or @UMMER.04!"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, ["ummer.04"])

    def test_system_keywords_excluded(self):
        desc = "Visit instagram.com/explore or instagram.com/reels or instagram.com/about"
        accounts = extract_instagram_accounts(desc)
        self.assertEqual(accounts, [])


class TestAutoVerificationService(unittest.TestCase):
    """Tests for matching description Instagram handles against the linked Arclent account."""

    def setUp(self):
        reset_dummy_linked_instagram_account()

    def tearDown(self):
        reset_dummy_linked_instagram_account()

    def test_case_1_direct_match(self):
        """Test 1: Direct match with @ummer.04."""
        desc = "Contributors: @ummer.04"
        result = verify_contribution_from_description(desc)
        self.assertTrue(result.verified)
        self.assertEqual(result.status, "auto_verified")
        self.assertEqual(result.method, "youtube_description_instagram_match")
        self.assertEqual(result.matched_account, "ummer.04")
        self.assertEqual(result.linked_account, "ummer.04")
        self.assertIn("@ummer.04", result.reason)

    def test_case_2_multiple_accounts_with_match(self):
        """Test 2: Multiple accounts containing the linked account."""
        desc = "Contributors: @john_doe @ummer.04 @alex123"
        result = verify_contribution_from_description(desc)
        self.assertTrue(result.verified)
        self.assertEqual(result.status, "auto_verified")
        self.assertEqual(result.matched_account, "ummer.04")

    def test_case_3_no_match(self):
        """Test 3: Instagram accounts exist but none match."""
        desc = "Contributors: @john_doe @alex123"
        result = verify_contribution_from_description(desc)
        self.assertFalse(result.verified)
        self.assertEqual(result.status, "fallback_no_match")
        self.assertIsNone(result.matched_account)
        self.assertIn("john_doe", result.extracted_accounts)
        self.assertIn("alex123", result.extracted_accounts)

    def test_case_4_no_instagram_account(self):
        """Test 4: Description contains no Instagram mentions."""
        desc = "Thanks to everyone who worked on this."
        result = verify_contribution_from_description(desc)
        self.assertFalse(result.verified)
        self.assertEqual(result.status, "fallback_no_instagram")
        self.assertIsNone(result.matched_account)
        self.assertEqual(result.extracted_accounts, [])

    def test_case_5_instagram_url_match(self):
        """Test 5: Match from an Instagram profile URL."""
        desc = "Contributor:\nhttps://instagram.com/ummer.04"
        result = verify_contribution_from_description(desc)
        self.assertTrue(result.verified)
        self.assertEqual(result.status, "auto_verified")
        self.assertEqual(result.matched_account, "ummer.04")

    def test_case_6_case_differences(self):
        """Test 6: Case difference (@UMMER.04 vs ummer.04)."""
        desc = "@UMMER.04 was the editor on this video."
        result = verify_contribution_from_description(desc)
        self.assertTrue(result.verified)
        self.assertEqual(result.status, "auto_verified")
        self.assertEqual(result.matched_account, "ummer.04")

    def test_case_7_empty_and_none_description(self):
        """Case D: Empty or unavailable description falls back gracefully."""
        res_empty = verify_contribution_from_description("")
        self.assertFalse(res_empty.verified)
        self.assertEqual(res_empty.status, "fallback_empty_description")

        res_none = verify_contribution_from_description(None)
        self.assertFalse(res_none.verified)
        self.assertEqual(res_none.status, "fallback_empty_description")

    def test_custom_linked_account_override(self):
        """Tests that passing a custom linked account or setting dummy linked account works cleanly."""
        set_dummy_linked_instagram_account("custom.creator")
        desc = "Video edited by @custom.creator"
        result = verify_contribution_from_description(desc)
        self.assertTrue(result.verified)
        self.assertEqual(result.matched_account, "custom.creator")

        # Explicit parameter override
        desc2 = "Assisted by @explicit_user"
        result2 = verify_contribution_from_description(desc2, linked_account="explicit_user")
        self.assertTrue(result2.verified)
        self.assertEqual(result2.matched_account, "explicit_user")

    def test_missing_linked_account(self):
        """Tests fallback when user has no linked account."""
        set_dummy_linked_instagram_account(None)
        desc = "Credits: @ummer.04"
        result = verify_contribution_from_description(desc)
        self.assertFalse(result.verified)
        self.assertEqual(result.status, "fallback_no_linked_account")


class TestAutoVerificationWorkflowIntegration(unittest.TestCase):
    """Integration tests testing /api/outreach/discover with mocked research graph."""

    def setUp(self):
        clear_all_sessions()
        reset_dummy_linked_instagram_account()
        self.client = TestClient(app)

    def tearDown(self):
        clear_all_sessions()
        reset_dummy_linked_instagram_account()

    @patch("app.api.outreach.execute_creator_research")
    def test_discover_auto_verified_when_description_matches(self, mock_research):
        """If YouTube video description contains @ummer.04, session is AUTO_VERIFIED."""
        mock_research.return_value = RawCreatorResearchResult(
            video_url="https://www.youtube.com/watch?v=0e3GPea1Tyg",
            creator_name="Test Creator",
            channel_name="Test Channel",
            video_title="Super Collab Project",
            video_description="Project created by XYZ.\nContributors:\n@ummer.04\n@alex123",
            description="Project created by XYZ.\nContributors:\n@ummer.04\n@alex123",
            selected_email="creator@test.com"
        )

        res = self.client.post("/api/outreach/discover", json={
            "youtube_url": "https://www.youtube.com/watch?v=0e3GPea1Tyg",
            "user_role": "Video editor"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.AUTO_VERIFIED)
        self.assertIsNotNone(data["auto_verification"])
        self.assertTrue(data["auto_verification"]["verified"])
        self.assertEqual(data["auto_verification"]["matched_account"], "ummer.04")

        # Verify session state in store
        session = get_session(data["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session.stage, OutreachStage.AUTO_VERIFIED)
        self.assertEqual(session.creator_response, "confirmed")
        self.assertIsNotNone(session.verified_at)

    @patch("app.api.outreach.execute_creator_research")
    def test_discover_fallback_when_description_does_not_match(self, mock_research):
        """If description contains other handles but not @ummer.04, falls back to existing workflow."""
        mock_research.return_value = RawCreatorResearchResult(
            video_url="https://www.youtube.com/watch?v=0e3GPea1Tyg",
            creator_name="Test Creator",
            channel_name="Test Channel",
            video_title="Super Collab Project",
            video_description="Contributors: @john_doe @alex123",
            description="Contributors: @john_doe @alex123",
            selected_email="creator@test.com"
        )

        res = self.client.post("/api/outreach/discover", json={
            "youtube_url": "https://www.youtube.com/watch?v=0e3GPea1Tyg",
            "user_role": "Video editor"
        })

        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Falls back to existing workflow stage
        self.assertEqual(data["stage"], OutreachStage.CREATOR_FOUND)
        self.assertIsNotNone(data["auto_verification"])
        self.assertFalse(data["auto_verification"]["verified"])
        self.assertEqual(data["auto_verification"]["status"], "fallback_no_match")

        # Verify session state is intact
        session = get_session(data["session_id"])
        self.assertIsNotNone(session)
        self.assertEqual(session.stage, OutreachStage.CREATOR_FOUND)
        self.assertEqual(session.creator_response, "pending")
