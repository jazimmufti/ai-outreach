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
        self.assertEqual(data["stage"], OutreachStage.VERIFY_INSTAGRAM)

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

    def test_oauth_state_generation_and_store(self):
        """Test a) OAuth state generation and PKCE code_verifier generation."""
        auth_url, state, code_verifier = generate_oauth_url()
        self.assertTrue(auth_url.startswith("https://accounts.google.com/o/oauth2/auth"))
        self.assertIn("response_type=code", auth_url)
        self.assertIn("code_challenge=", auth_url)
        self.assertIn("code_challenge_method=S256", auth_url)
        self.assertGreaterEqual(len(state), 32)
        self.assertGreaterEqual(len(code_verifier), 43)

        # Verify b) PKCE verifier persistence
        persisted_verifier = get_oauth_code_verifier(state)
        self.assertEqual(persisted_verifier, code_verifier)

        # Cleanup
        remove_oauth_session(state)
        self.assertIsNone(get_oauth_code_verifier(state))

    def test_connect_endpoint_and_callback_exact_state(self):
        """Test c) and f): /connect endpoint creates state, and callback using exact state succeeds without cookie dependency."""
        from unittest.mock import patch

        # 1. Call /api/gmail/connect (without setting cookies or in separate request context)
        connect_res = self.client.get("/api/gmail/connect")
        self.assertEqual(connect_res.status_code, 200)
        connect_data = connect_res.json()
        state = connect_data["state"]
        self.assertTrue(state)

        # Verify PKCE verifier is stored server-side
        code_verifier = get_oauth_code_verifier(state)
        self.assertIsNotNone(code_verifier)

        # 2. Simulate Google redirecting back to /api/gmail/callback with exact state and code
        with patch("app.api.gmail.exchange_code_for_tokens") as mock_exchange:
            mock_exchange.return_value = {
                "connected": True,
                "email": "test-creator@gmail.com",
                "scopes": ["https://www.googleapis.com/auth/gmail.send"]
            }

            # Callback in a fresh client / without session cookie to simulate cross-site popup
            callback_res = self.client.get(f"/api/gmail/callback?code=mock_auth_code_12345&state={state}")
            self.assertEqual(callback_res.status_code, 200)
            self.assertIn("Gmail Account Linked!", callback_res.text)
            self.assertIn("test-creator@gmail.com", callback_res.text)
            mock_exchange.assert_called_once()
            
            # Verify the exact code and state were exchanged with the saved code_verifier
            called_kwargs = mock_exchange.call_args.kwargs
            self.assertEqual(called_kwargs["code"], "mock_auth_code_12345")
            self.assertEqual(called_kwargs["state"], state)
            self.assertEqual(called_kwargs["code_verifier"], code_verifier)

    def test_callback_rejects_unknown_or_invalid_state(self):
        """Test d) Invalid / unknown state is strictly rejected with 400 and expired/invalid message."""
        res = self.client.get("/api/gmail/callback?code=some_code&state=completely_invalid_state_123")
        self.assertEqual(res.status_code, 400)
        self.assertIn("OAuth Session Timed Out", res.text)
        self.assertIn("The verification token for this authorization attempt expired or was already used.", res.text)

    def test_callback_rejects_expired_state(self):
        """Test e) Expired OAuth state (older than TTL) is rejected."""
        import time
        from app.services.gmail_service import _oauth_transaction_store, _store_lock

        expired_state = "expired_test_state_99999"
        with _store_lock:
            _oauth_transaction_store[expired_state] = {
                "code_verifier": "test_verifier_content_12345",
                "created_at": time.time() - 1000  # 1000 seconds ago (> 900s TTL)
            }

        # get_oauth_code_verifier should return None for expired state
        self.assertIsNone(get_oauth_code_verifier(expired_state))

        # Callback should reject expired state
        res = self.client.get(f"/api/gmail/callback?code=valid_code&state={expired_state}")
        self.assertEqual(res.status_code, 400)
        self.assertIn("OAuth Session Timed Out", res.text)

    def test_stateless_oauth_state_recovery_across_server_restarts(self):
        """Test that state and PKCE verifier are recoverable even if memory store is wiped (simulating a new worker/container on Railway)."""
        from app.services.gmail_service import _oauth_transaction_store, _store_lock

        auth_url, state, code_verifier = generate_oauth_url()

        # Simulate Worker A shutting down or request routed to Worker B by wiping memory store
        with _store_lock:
            _oauth_transaction_store.clear()

        # Worker B receives callback with state and successfully recovers code_verifier
        recovered_verifier = get_oauth_code_verifier(state)
        self.assertEqual(recovered_verifier, code_verifier)


if __name__ == "__main__":
    unittest.main()


