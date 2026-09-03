"""Dedicated tests for the 2-step verification flow (1 · EMAIL, 2 · INSTAGRAM)."""

import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    CreatorProfile,
    EmailCandidate,
    SocialProfile,
    OutreachStage
)
from app.services.session_manager import create_session, get_session, clear_all_sessions


class TestVerificationFlow(unittest.TestCase):
    """Test suite covering the 2-step verification endpoints and state transitions."""

    def setUp(self):
        clear_all_sessions()
        self.client = TestClient(app)

    def tearDown(self):
        clear_all_sessions()

    def test_step_1_confirm_email_yes(self):
        """Step 1: User confirms the discovered email."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Antarctica Video"
        )
        session.discovered_email = EmailCandidate(
            email="contact@mrbeast.com",
            source="YouTube Description",
            confidence="high"
        )

        res = self.client.post("/api/outreach/confirm-email", json={
            "session_id": session.session_id,
            "email_confirmed": True,
            "user_role": "Video editor"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.VERIFY_INSTAGRAM)
        self.assertEqual(data["final_email"], "contact@mrbeast.com")
        self.assertTrue(data["email_confirmed"])

    def test_step_1_confirm_email_no(self):
        """Step 1: User rejects the discovered email (not them / skip)."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(name="MrBeast", channel_name="MrBeast")
        session.discovered_email = EmailCandidate(
            email="wrong@mrbeast.com",
            source="YouTube Description",
            confidence="high"
        )

        res = self.client.post("/api/outreach/confirm-email", json={
            "session_id": session.session_id,
            "email_confirmed": False
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.VERIFY_INSTAGRAM)
        self.assertIsNone(data["final_email"])
        self.assertFalse(data["email_confirmed"])

    def test_step_2_confirm_instagram_yes(self):
        """Step 2: User confirms the discovered Instagram profile."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(name="MrBeast", channel_name="MrBeast")
        session.instagram_profile = SocialProfile(
            platform="Instagram",
            username="@mrbeast",
            url="https://instagram.com/mrbeast",
            confidence="high"
        )

        res = self.client.post("/api/outreach/confirm-instagram", json={
            "session_id": session.session_id,
            "instagram_confirmed": True,
            "user_role": "Thumbnail designer"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.OUTREACH_HUB)
        self.assertEqual(data["final_instagram_handle"], "@mrbeast")
        self.assertEqual(data["final_instagram_url"], "https://instagram.com/mrbeast")
        self.assertTrue(data["instagram_confirmed"])

    def test_step_1_manual_email_entry(self):
        """Step 1 Fallback: User manually enters a contact email address."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(name="Creator", channel_name="Channel")

        res = self.client.post("/api/outreach/manual-email", json={
            "session_id": session.session_id,
            "email": "editor_contact@creator.com",
            "user_role": "Video editor"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["final_email"], "editor_contact@creator.com")
        self.assertTrue(data["email_confirmed"])

    def test_step_2_manual_instagram_entry(self):
        """Step 2 Fallback: User enters a custom Instagram handle or URL."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(name="Creator", channel_name="Channel")

        # Test entering URL
        res = self.client.post("/api/outreach/manual-instagram", json={
            "session_id": session.session_id,
            "handle": "https://instagram.com/custom_creator",
            "user_role": "Editor"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["final_instagram_handle"], "@custom_creator")
        self.assertEqual(data["final_instagram_url"], "https://instagram.com/custom_creator")
        self.assertTrue(data["instagram_confirmed"])


    def test_direct_send_email_and_verification(self):
        """Test sending email directly with generated confirmation tokens and creator verification."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.final_email = "verified@mrbeast.com"
        session.email_confirmed = True

        # Test verification confirmation via email link
        res = self.client.get(f"/api/outreach/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Collaboration Confirmed!", res.text)
        self.assertIn("MrBeast", res.text)

        updated = get_session(session.session_id)
        self.assertEqual(updated.creator_response, "confirmed")
        self.assertEqual(updated.stage, OutreachStage.VERIFIED)

    def test_direct_send_email_and_rejection(self):
        """Test sending email directly with creator rejection response."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.final_email = "verified@mrbeast.com"

        # Test verification rejection via email link
        res = self.client.get(f"/api/outreach/verify?session_id={session.session_id}&action=reject")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Response Recorded", res.text)

    def test_verify_root_interactive_page(self):
        """Test visiting root /verify with session_id renders interactive approval and rejection page."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.user_role = "Lead Video Editor"

        # Test visiting interactive /verify landing page (no action specified)
        res = self.client.get(f"/verify?session_id={session.session_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Can you confirm this collaboration?", res.text)
        self.assertIn("Yes, I confirm this collaboration", res.text)
        self.assertIn("No, I do not confirm", res.text)
        self.assertIn("MrBeast", res.text)
        self.assertIn("Lead Video Editor", res.text)
        self.assertIn("Squid Game In Real Life", res.text)

    def test_verify_root_confirm_action(self):
        """Test confirming collaboration from root /verify endpoint."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )

        res = self.client.get(f"/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Collaboration Confirmed!", res.text)

        updated = get_session(session.session_id)
        self.assertEqual(updated.creator_response, "confirmed")
        self.assertEqual(updated.stage, OutreachStage.VERIFIED)

    def test_verify_root_reject_action(self):
        """Test rejecting collaboration from root /verify endpoint."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )

        res = self.client.get(f"/verify?session_id={session.session_id}&action=reject")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Response Recorded", res.text)

        updated = get_session(session.session_id)
        self.assertEqual(updated.creator_response, "rejected")
        self.assertEqual(updated.stage, OutreachStage.REJECTED)

    def test_verify_missing_session_id(self):
        """Test visiting /verify without session_id returns 400 Bad Request."""
        res = self.client.get("/verify")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Arclent Collaboration Verification", res.text)


if __name__ == "__main__":
    unittest.main()

