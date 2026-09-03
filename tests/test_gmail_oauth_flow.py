"""Comprehensive verification test suite for Gmail OAuth 2.0 Flow, Redirect URI Resolution, and PKCE State Handling."""

import os
import json
import time
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.gmail_service import (
    generate_oauth_url,
    exchange_code_for_tokens,
    get_stored_credentials,
    get_gmail_status,
    encode_signed_oauth_state,
    decode_signed_oauth_state,
    get_oauth_code_verifier,
    store_oauth_session,
    remove_oauth_session,
    _consumed_oauth_states,
    _oauth_transaction_store
)


class TestGmailOAuthFlow(unittest.TestCase):
    """Test suite covering redirect URI resolution, state signing, token precedence, and callback routing."""

    def setUp(self):
        self.client = TestClient(app)

    def test_redirect_uri_default_local(self):
        """Test default local redirect URI resolution."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            uri = settings.get_redirect_uri()
            self.assertEqual(uri, "http://localhost:8000/api/gmail/callback")

    def test_redirect_uri_railway_os_env_precedence(self):
        """Test Railway OS environment variable takes precedence over default and .env values."""
        prod_uri = "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback"
        with patch.dict(os.environ, {"GOOGLE_REDIRECT_URI": prod_uri}, clear=True):
            settings = Settings()
            self.assertTrue(settings.is_redirect_uri_from_env())
            self.assertEqual(settings.get_redirect_uri(), prod_uri)

    def test_redirect_uri_sanitization_quotes_and_whitespace(self):
        """Test accidental quotes and whitespace are stripped from GOOGLE_REDIRECT_URI."""
        raw_uri = '  "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback"  '
        with patch.dict(os.environ, {"GOOGLE_REDIRECT_URI": raw_uri}, clear=True):
            settings = Settings()
            self.assertEqual(
                settings.get_redirect_uri(),
                "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback"
            )

    def test_redirect_uri_trailing_slash_normalization(self):
        """Test trailing slash is stripped from redirect URI."""
        slash_uri = "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback/"
        with patch.dict(os.environ, {"GOOGLE_REDIRECT_URI": slash_uri}, clear=True):
            settings = Settings()
            self.assertEqual(
                settings.get_redirect_uri(),
                "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback"
            )

    def test_client_id_and_secret_quote_sanitization(self):
        """Test surrounding quotes on GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are stripped."""
        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": '"857375356408-mockclientid.apps.googleusercontent.com"',
            "GOOGLE_CLIENT_SECRET": "'GOCSPX-mocksecret123'"
        }, clear=True):
            settings = Settings()
            self.assertEqual(settings.get_google_client_id(), "857375356408-mockclientid.apps.googleusercontent.com")
            self.assertEqual(settings.get_google_client_secret(), "GOCSPX-mocksecret123")

    def test_auth_url_and_exchange_use_same_redirect_uri(self):
        """Test generate_oauth_url and exchange_code_for_tokens use identical redirect URI."""
        prod_uri = "https://ai-outreach-production-8dcc.up.railway.app/api/gmail/callback"
        with patch.object(Settings, "get_redirect_uri", return_value=prod_uri):
            with patch.object(Settings, "get_google_client_id", return_value="mock-client-id-12345678"):
                with patch.object(Settings, "get_google_client_secret", return_value="mock-client-secret-123"):
                    with patch("google_auth_oauthlib.flow.Flow.from_client_config") as mock_flow_cls:
                        mock_flow = MagicMock()
                        mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?...", "test-state")
                        mock_flow.credentials = MagicMock()
                        mock_flow.credentials.to_json.return_value = "{}"
                        mock_flow_cls.return_value = mock_flow

                        # 1. Generate auth URL
                        generate_oauth_url()
                        mock_flow_cls.assert_called()
                        call_args_init = mock_flow_cls.call_args[1]
                        self.assertEqual(call_args_init["redirect_uri"], prod_uri)

                        # 2. Exchange code
                        exchange_code_for_tokens(code="mock-code", state="test-state", code_verifier="mock-verifier")
                        call_args_exchange = mock_flow_cls.call_args[1]
                        self.assertEqual(call_args_exchange["redirect_uri"], prod_uri)

    def test_pkce_signed_state_roundtrip(self):
        """Test cryptographic signing and decoding of PKCE state verifier."""
        verifier = "sample_high_entropy_pkce_verifier_string_1234567890"
        signed_state = encode_signed_oauth_state(verifier)
        self.assertIsInstance(signed_state, str)
        self.assertTrue(len(signed_state) > 30)

        # Decode
        recovered = decode_signed_oauth_state(signed_state)
        self.assertEqual(recovered, verifier)

    def test_pkce_signed_state_tamper_rejection(self):
        """Test tampered signed state returns None."""
        verifier = "sample_verifier_string"
        signed_state = encode_signed_oauth_state(verifier)
        tampered_state = signed_state[:-4] + "AAAA"
        self.assertIsNone(decode_signed_oauth_state(tampered_state))

    def test_pkce_signed_state_replay_prevention(self):
        """Test that consumed state tokens cannot be replayed."""
        verifier = "sample_verifier_for_replay"
        signed_state = encode_signed_oauth_state(verifier)

        # First retrieval succeeds
        retrieved = decode_signed_oauth_state(signed_state)
        self.assertEqual(retrieved, verifier)

        # Mark consumed
        remove_oauth_session(signed_state)

        # Replay attempt fails
        replayed = decode_signed_oauth_state(signed_state)
        self.assertIsNone(replayed)

    def test_token_file_priority_over_env_json(self):
        """Test get_stored_credentials prioritizes active disk token.json over GMAIL_TOKEN_JSON env."""
        mock_disk_creds = MagicMock()
        mock_disk_creds.expired = False
        mock_disk_creds.valid = True

        with patch("os.path.exists", return_value=True):
            with patch("google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=mock_disk_creds) as mock_disk_loader:
                with patch("google.oauth2.credentials.Credentials.from_authorized_user_info") as mock_env_loader:
                    creds = get_stored_credentials()
                    self.assertIsNotNone(creds)
                    mock_disk_loader.assert_called_once()
                    mock_env_loader.assert_not_called()

    def test_callback_endpoint_missing_code_or_state(self):
        """Test GET /api/gmail/callback with missing params returns 400."""
        res = self.client.get("/api/gmail/callback")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid Callback Request", res.text)

    def test_callback_endpoint_with_google_error(self):
        """Test GET /api/gmail/callback with Google error query returns cancelled page."""
        res = self.client.get("/api/gmail/callback?error=access_denied")
        self.assertEqual(res.status_code, 400)
        self.assertIn("CONNECTION CANCELLED", res.text)
        self.assertIn("access_denied", res.text)

    def test_callback_endpoint_expired_state(self):
        """Test GET /api/gmail/callback with invalid or expired state returns expired page."""
        res = self.client.get("/api/gmail/callback?code=mock_code&state=invalid_unregistered_state")
        self.assertEqual(res.status_code, 400)
        self.assertIn("SESSION EXPIRED", res.text)


if __name__ == "__main__":
    unittest.main()
