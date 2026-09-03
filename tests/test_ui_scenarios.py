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

    def test_scenario_b_email_and_instagram_verification_screens(self):
        """Scenario B: 2-step verification screens (1 · EMAIL and 2 · INSTAGRAM) exist in HTML."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.text

        # Verify Step 1: EMAIL Verification Screen and Elements
        self.assertIn("screen-verify-email", html)
        self.assertIn("1 · EMAIL", html)
        self.assertIn("Confirm Contact Email", html)
        self.assertIn("btn-email-confirm-yes", html)
        self.assertIn("btn-email-confirm-no", html)
        self.assertIn("btn-back-email", html)
        self.assertIn("email-manual-entry-form", html)
        self.assertIn("btn-email-manual-submit", html)
        self.assertIn("btn-email-skip-to-ig", html)

        # Verify Step 2: INSTAGRAM Verification Screen and Elements
        self.assertIn("screen-verify-instagram", html)
        self.assertIn("2 · INSTAGRAM", html)
        self.assertIn("Confirm Instagram Profile", html)
        self.assertIn("btn-ig-confirm-yes", html)
        self.assertIn("btn-ig-confirm-no", html)
        self.assertIn("btn-back-ig", html)
        self.assertIn("ig-manual-entry-form", html)
        self.assertIn("ig-confirmed-view", html)
        self.assertIn("btn-ig-open-send", html)
        self.assertIn("btn-ig-copy-draft-main", html)
        self.assertIn("ig-confirmed-other-socials-box", html)

        # Verify Outreach Hub Screen
        self.assertIn("screen-outreach-hub", html)
        self.assertIn("btn-back-hub", html)
        self.assertIn("workflow-email-form", html)
        self.assertIn("hub-instagram-block", html)

        # Verify Delivery Screen
        self.assertIn("screen-delivery-success", html)
        self.assertIn("btn-back-delivery", html)

    def test_scenario_c_no_demo_simulation_controls(self):
        """Scenario C: Verify absolutely NO mock controls, state selectors, or fake demo buttons exist."""
        res = self.client.get("/")
        html = res.text

        # Verify no demo/simulation artifacts
        self.assertNotIn("emailScenario", html)
        self.assertNotIn("igScenario", html)
        self.assertNotIn("PROTOTYPE CONTROLS", html)
        self.assertNotIn("restart()", html)

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
