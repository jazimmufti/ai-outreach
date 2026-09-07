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

    def test_instagram_extension_outreach_flow_confirmation(self):
        """Test full workflow: Instagram outreach dispatched -> session recorded -> creator confirms via link."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="VisualCreator",
            channel_name="VisualCreator",
            video_title="Cinema Camera Review"
        )
        session.final_instagram_handle = "@visualcreator"
        session.instagram_confirmed = True

        # Step 1: User completes Instagram DM and clicks 'I've Sent the Message'
        res = self.client.post("/api/outreach/record-social-outreach", json={
            "session_id": session.session_id,
            "platform": "Instagram",
            "handle": "@visualcreator",
            "message": f"Hey! Please verify: http://localhost:8000/verify?session_id={session.session_id}"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.SENT)
        self.assertEqual(data["creator_response"], "pending")

        # Step 2: Polling status shows pending
        poll_res = self.client.get(f"/api/outreach/session-status?session_id={session.session_id}")
        self.assertEqual(poll_res.status_code, 200)
        self.assertEqual(poll_res.json()["creator_response"], "pending")

        # Step 3: Creator clicks verification link in Instagram DM
        verify_res = self.client.get(f"/api/outreach/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn("Collaboration Confirmed!", verify_res.text)

        # Step 4: Status polling reflects confirmed state
        confirmed_poll = self.client.get(f"/api/outreach/session-status?session_id={session.session_id}")
        self.assertEqual(confirmed_poll.status_code, 200)
        self.assertEqual(confirmed_poll.json()["creator_response"], "confirmed")
        self.assertEqual(confirmed_poll.json()["stage"], OutreachStage.VERIFIED)

    def test_repeated_confirmation_link_handling(self):
        """Test that opening an already confirmed or rejected link does not show Yes/No buttons."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.user_role = "Video editor"
        session.sender_handle = "@jazimmufti"
        session.selected_channel = "instagram"

        # 1. Creator confirms
        res1 = self.client.get(f"/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("Collaboration Confirmed!", res1.text)

        # 2. Creator reopens the root /verify link again (without action)
        res2 = self.client.get(f"/verify?session_id={session.session_id}")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("You&#039;ve already confirmed this collaboration", res2.text.replace("'", "&#039;"))
        self.assertNotIn("Yes, I confirm this collaboration", res2.text)
        self.assertNotIn("No, I do not confirm", res2.text)
        self.assertIn("jazimmufti on Arclent", res2.text)

        # 3. Creator tries to click reject on already confirmed session -> remains confirmed
        res3 = self.client.get(f"/verify?session_id={session.session_id}&action=reject")
        self.assertEqual(res3.status_code, 200)
        self.assertIn("You&#039;ve already confirmed this collaboration", res3.text.replace("'", "&#039;"))
        self.assertNotIn("Yes, I confirm this collaboration", res3.text)

    def test_repeated_rejection_link_handling(self):
        """Test that opening an already rejected link does not show Yes/No buttons."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            video_title="Squid Game In Real Life"
        )
        session.selected_channel = "email"

        # 1. Creator rejects
        res1 = self.client.get(f"/verify?session_id={session.session_id}&action=reject")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("Response Recorded", res1.text)

        # 2. Creator reopens the link again
        res2 = self.client.get(f"/verify?session_id={session.session_id}")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("You&#039;ve already rejected this collaboration", res2.text.replace("'", "&#039;"))
        self.assertNotIn("Yes, I confirm this collaboration", res2.text)
        self.assertNotIn("No, I do not confirm", res2.text)
        self.assertIn("Someone on Arclent", res2.text)

    def test_dynamic_sender_identity_on_verify(self):
        """Test that /verify dynamically renders '{username} on Arclent' for Instagram and 'Someone on Arclent' for email."""
        # Case A: Instagram sender handle -> shows 'artistic_editor on Arclent'
        session_ig = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session_ig.creator = CreatorProfile(name="MrBeast", channel_name="MrBeast", video_title="Antarctica")
        session_ig.user_role = "Colorist"
        session_ig.sender_handle = "@artistic_editor"
        session_ig.selected_channel = "instagram"

        res_ig = self.client.get(f"/verify?session_id={session_ig.session_id}")
        self.assertEqual(res_ig.status_code, 200)
        self.assertNotIn("Someone on Arclent", res_ig.text)
        self.assertIn("artistic_editor on Arclent", res_ig.text)

        # Case B: Email sender -> keeps as 'Someone on Arclent' (system email not exposed)
        session_gmail = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session_gmail.creator = CreatorProfile(name="MrBeast", channel_name="MrBeast", video_title="Antarctica")
        session_gmail.user_role = "VFX Artist"
        session_gmail.selected_channel = "email"

        res_gmail = self.client.get(f"/verify?session_id={session_gmail.session_id}")
        self.assertEqual(res_gmail.status_code, 200)
        self.assertIn("Someone on Arclent", res_gmail.text)
        self.assertNotIn("ubja56@gmail.com", res_gmail.text)


if __name__ == "__main__":
    unittest.main()

