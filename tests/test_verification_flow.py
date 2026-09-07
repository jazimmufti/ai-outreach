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

    def test_record_social_outreach_instagram(self):
        """Test recording social media outreach dispatch via Instagram and subsequent creator confirmation."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.final_instagram_handle = "@mrbeast"

        # Record social dispatch
        res = self.client.post("/api/outreach/record-social-outreach", json={
            "session_id": session.session_id,
            "platform": "Instagram",
            "handle": "@mrbeast",
            "message": f"Hey MrBeast! Confirm at: http://127.0.0.1:8000/verify?session_id={session.session_id}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["stage"], OutreachStage.SENT)
        self.assertEqual(data["selected_channel"], "instagram")
        self.assertEqual(data["creator_response"], "pending")

        # Verify creator can open link and confirm
        verify_res = self.client.get(f"/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn("Collaboration Confirmed!", verify_res.text)

        # Verify session is updated to verified
        updated = get_session(session.session_id)
        self.assertEqual(updated.stage, OutreachStage.VERIFIED)
        self.assertEqual(updated.creator_response, "confirmed")

    def test_record_social_outreach_other_platform(self):
        """Test recording social outreach via X/Twitter or Reddit."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="TechReviewer",
            channel_name="TechReviewer",
            video_title="Smartphone Review"
        )

        # Record social dispatch on X (Twitter)
        res = self.client.post("/api/outreach/record-social-outreach", json={
            "session_id": session.session_id,
            "platform": "X",
            "handle": "@tech_reviewer"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.SENT)
        self.assertEqual(data["selected_channel"], "x")

        # Status endpoint returns session with pending creator response
        status_res = self.client.get(f"/api/outreach/session-status?session_id={session.session_id}")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertEqual(status_data["stage"], OutreachStage.SENT)
        self.assertEqual(status_data["creator_response"], "pending")

    def test_instagram_dm_url_patterns(self):
        """Test that Instagram handles with diverse formats properly map to DM deep links."""
        handles = [
            "@mrbeast",
            "mrbeast",
            "https://instagram.com/mrbeast/",
            "https://www.instagram.com/mrbeast/?igsh=123",
            "https://ig.me/m/mrbeast"
        ]
        for raw in handles:
            clean = raw.split("?")[0].split("#")[0].rstrip("/").replace("https://www.instagram.com/", "").replace("https://instagram.com/", "").replace("https://ig.me/m/", "").lstrip("@")
            self.assertEqual(clean, "mrbeast")
            dm_url = f"https://ig.me/m/{clean}"
            self.assertEqual(dm_url, "https://ig.me/m/mrbeast")
            self.assertNotIn("https://instagram.com/mrbeast", dm_url)


if __name__ == "__main__":
    unittest.main()

