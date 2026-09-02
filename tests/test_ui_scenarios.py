"""Integration and UI scenario verification test suite."""

import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    CreatorProfile,
    EmailCandidate,
    SocialProfile,
    OutreachStage
)
from app.services.session_manager import create_session, get_session

class TestUIScenariosAndBranding(unittest.TestCase):
    """Test suite verifying all user scenarios and branding requirements."""

    def setUp(self):
        self.client = TestClient(app)

    def test_scenario_d_branding_assets_and_html(self):
        """Scenario D: Verify Arclent logo asset is served, title is updated, and no old CreatorOutreach branding exists."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # 1. Verify Page Title
        self.assertIn("Arclent — Creator Collaboration Verification & Outreach", html)
        self.assertNotIn("<title>Creator Discovery + Email Outreach</title>", html)

        # 2. Verify Arclent Logo Image is present in header
        self.assertIn('/static/arclent-logo.png', html)
        self.assertIn('alt="Arclent"', html)

        # 3. Verify static logo file is downloadable
        logo_res = self.client.get("/static/arclent-logo.png")
        self.assertEqual(logo_res.status_code, 200)
        self.assertEqual(logo_res.headers.get("content-type"), "image/png")

        # 4. Verify no old visible brand text
        self.assertNotIn("CREATOR<span>OUTREACH</span>", html)
        self.assertNotIn('<div class="brand-badge">SaaS</div>', html)

        # 5. Verify demo simulator button is removed
        self.assertNotIn("simulate-creator-confirm-btn", html)
        self.assertNotIn("DEMO SIMULATION", html)

    def test_scenario_b_no_email_with_social_profiles(self):
        """Scenario B: Email Not Found + Social Profiles Found."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify positive, reassuring fallback UI elements in HTML
        self.assertIn("No public email listed on this YouTube channel? No worries!", html)
        self.assertIn("Verified Social Media Profiles", html)
        self.assertIn("noemail-socials-grid", html)
        self.assertIn("noemail-copy-pitch-body", html)
        self.assertIn("noemail-pitch-copy-btn", html)
        self.assertIn("noemail-manual-email-form", html)

    def test_scenario_c_no_email_no_socials_empty_state(self):
        """Scenario C: Verify graceful empty state when neither email nor socials are found."""
        res = self.client.get("/")
        html = res.text

        # Verify polite empty state container exists
        self.assertIn("noemail-socials-empty", html)
        self.assertIn("No public social profiles found", html)

    def test_scenario_a_email_found_preserves_flow(self):
        """Scenario A: Creator has a publicly available email."""
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

        # Confirm step
        res = self.client.post("/api/outreach/confirm", json={
            "session_id": session.session_id,
            "creator_confirmed": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stage"], OutreachStage.MESSAGE_DRAFT)
        self.assertEqual(data["final_email"], "rick@astleymusic.com")
        self.assertIsNotNone(data.get("message"))

    def test_recipient_verification_endpoint(self):
        """Verify that recipient clicking official confirmation link marks session verified."""
        session = create_session("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        session.creator = CreatorProfile(
            name="MrBeast",
            channel_name="MrBeast",
            subscriber_count="350M subscribers"
        )
        session.stage = OutreachStage.SENT

        res = self.client.get(f"/api/outreach/verify?session_id={session.session_id}&action=confirm")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Collaboration Confirmed!", res.text)
        
        updated = get_session(session.session_id)
        self.assertEqual(updated.creator_response, "confirmed")
        self.assertEqual(updated.stage, OutreachStage.VERIFIED)


if __name__ == "__main__":
    unittest.main()
