"""Automated verification test suite for Creator Discovery and Step-by-Step Outreach Workflow."""

import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.services.youtube_service import extract_video_id
from app.services.social_discovery import extract_social_profiles
from app.services.email_discovery import extract_emails_from_text
from app.services.session_manager import create_session, get_session
from app.models.schemas import CreatorProfile, EmailCandidate, SocialProfile, OutreachStage
from app.services.message_generator import generate_outreach_message
from app.services.gmail_service import (
    generate_oauth_url,
    get_oauth_code_verifier,
    store_oauth_session,
    remove_oauth_session
)


class TestCreatorOutreachPipeline(unittest.TestCase):
    """Test suite for core components and step-by-step workflow."""

    def setUp(self):
        self.client = TestClient(app)

    def test_youtube_url_extraction(self):
        """Test video ID extraction across various URL formats."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share", "dQw4w9WgXcQ"),
        ]
        for url, expected_id in test_cases:
            vid = extract_video_id(url)
            self.assertEqual(vid, expected_id, f"Failed on {url}")

    def test_social_extraction_strictly_allowed_platforms(self):
        """Test that ONLY Instagram, X, Discord, Reddit, and Facebook are extracted."""
        sample_text = (
            "Follow my socials:\n"
            "Instagram: https://instagram.com/creator_studio\n"
            "Twitter/X: https://x.com/creator\n"
            "Discord Server: https://discord.gg/creatorhub\n"
            "Reddit: https://reddit.com/r/creatorcommunity\n"
            "Facebook: https://facebook.com/creatorpage\n"
            "LinkedIn: https://linkedin.com/in/creator-name\n"
            "GitHub: https://github.com/creatorexpert\n"
            "Portfolio: https://creatorportfolio.dev"
        )
        socials = extract_social_profiles(sample_text)
        platforms = {s.platform for s in socials}
        
        self.assertIn("Instagram", platforms)
        self.assertIn("X", platforms)
        self.assertIn("Discord", platforms)
        self.assertIn("Reddit", platforms)
        self.assertIn("Facebook", platforms)
        self.assertIn("LinkedIn", platforms)

        self.assertNotIn("GitHub", platforms)
        self.assertNotIn("Website", platforms)

    def test_email_extraction_and_cleaning(self):
        """Test deterministic email parsing and obfuscation handling."""
        sample_text = (
            "For business inquiries only: business@creatorstudio.com\n"
            "Management: contact [at] creatoragency [dot] io\n"
            "Spam filter check: noreply@youtube.com should be ignored\n"
            "Icon check: avatar.png@2x should be ignored"
        )
        candidates = extract_emails_from_text(sample_text)
        emails = [c.email for c in candidates]
        self.assertIn("business@creatorstudio.com", emails)
        self.assertIn("contact@creatoragency.io", emails)
        self.assertNotIn("noreply@youtube.com", emails)

    def test_api_health_endpoint(self):
        """Test FastAPI health check endpoint."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_gmail_status_endpoint(self):
        """Test Gmail status endpoint."""
        res = self.client.get("/api/gmail/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("connected", data)

    def test_workflow_confirm_yes_path(self):
        """Test Step 3 Confirmation: 'Yes, that's them' locks creator & generates email draft."""
        session = create_session("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        session.creator = CreatorProfile(
            name="Rick Astley",
            channel_name="RickAstleyVEVO",
            channel_handle="@RickAstleyYT",
            video_title="Never Gonna Give You Up"
        )
        session.discovered_email = EmailCandidate(
            email="rick@astleymusic.com",
            source="YouTube Description",
            source_type="publicly_published",
            confidence="high"
        )

        res = self.client.post("/api/outreach/confirm", json={
            "session_id": session.session_id,
            "creator_confirmed": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.MESSAGE_DRAFT)
        self.assertEqual(data["final_email"], "rick@astleymusic.com")
        self.assertIsNotNone(data.get("message"))
        self.assertIn("subject", data["message"])
        self.assertIn("body", data["message"])

    def test_workflow_confirm_no_path(self):
        """Test Step 3 Confirmation: 'No, that's not them' discards discovered email & redirects to manual entry."""
        session = create_session("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        session.creator = CreatorProfile(
            name="Rick Astley",
            channel_name="RickAstleyVEVO",
            channel_handle="@RickAstleyYT"
        )
        session.discovered_email = EmailCandidate(
            email="wrong@domain.com",
            source="YouTube Description",
            source_type="publicly_published",
            confidence="high"
        )

        res = self.client.post("/api/outreach/confirm", json={
            "session_id": session.session_id,
            "creator_confirmed": False
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.MANUAL_EMAIL_INPUT)
        self.assertIsNone(data["final_email"])
        self.assertIsNone(data["discovered_email"])

    def test_workflow_manual_email_validation(self):
        """Test Step 3 Fallback: RFC email validation and user_provided status."""
        session = create_session("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        session.creator = CreatorProfile(
            name="Rick Astley",
            channel_name="RickAstleyVEVO"
        )

        # 1. Invalid email check
        bad_res = self.client.post("/api/outreach/manual-email", json={
            "session_id": session.session_id,
            "email": "invalid_email_without_at"
        })
        self.assertEqual(bad_res.status_code, 422)

        # 2. Valid email check
        good_res = self.client.post("/api/outreach/manual-email", json={
            "session_id": session.session_id,
            "email": "correct-contact@astleystudio.com"
        })
        self.assertEqual(good_res.status_code, 200)
        data = good_res.json()
        self.assertEqual(data["final_email"], "correct-contact@astleystudio.com")
        self.assertEqual(data["email_verification_status"], "user_provided")
        self.assertEqual(data["stage"], OutreachStage.MESSAGE_DRAFT)

    def test_workflow_message_generation_channels(self):
        """Test multi-channel message generation for Email, Instagram, and Manual copy."""
        session = create_session("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        session.creator = CreatorProfile(
            name="Tech Reviewer",
            channel_name="TechDaily",
            video_title="Top 10 Gadgets"
        )

        # 1. Instagram Channel (Must not have subject)
        insta_res = self.client.post("/api/outreach/generate-message", json={
            "session_id": session.session_id,
            "channel": "instagram"
        })
        self.assertEqual(insta_res.status_code, 200)
        insta_data = insta_res.json()
        self.assertEqual(insta_data["stage"], OutreachStage.INSTAGRAM_READY)
        self.assertIsNone(insta_data["message"]["subject"])
        self.assertGreater(len(insta_data["message"]["body"]), 20)

        # 2. Email Channel (Must have subject)
        email_res = self.client.post("/api/outreach/generate-message", json={
            "session_id": session.session_id,
            "channel": "email"
        })
        self.assertEqual(email_res.status_code, 200)
        email_data = email_res.json()
        self.assertEqual(email_data["stage"], OutreachStage.MESSAGE_DRAFT)
        self.assertIsNotNone(email_data["message"]["subject"])

        # 3. Manual Channel
        manual_res = self.client.post("/api/outreach/generate-message", json={
            "session_id": session.session_id,
            "channel": "manual"
        })
        self.assertEqual(manual_res.status_code, 200)
        manual_data = manual_res.json()
        self.assertEqual(manual_data["stage"], OutreachStage.MANUAL_MESSAGE_READY)


if __name__ == "__main__":
    unittest.main()
