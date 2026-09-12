"""Tests for Discord integration: discovery, snowflake validation, service mocking, and API endpoints."""

import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings, Settings
from app.services.social_discovery import extract_discord_information, extract_social_profiles
from app.services.discord_service import (
    validate_snowflake,
    verify_bot_connection,
    send_dm_message,
    DiscordConfigurationError,
    DiscordValidationError,
    DiscordAuthenticationError,
    DiscordDeliveryError,
    DiscordNotFoundError,
    DiscordRateLimitError,
)
from app.services.message_generator import generate_outreach_message
from app.services.session_manager import create_session, get_session
from app.models.schemas import (
    CreatorProfile,
    DiscordProfile,
    OutreachStage,
)


class TestDiscordIntegration(unittest.IsolatedAsyncioTestCase):
    """Test suite for Arclent Discord Bot outreach integration."""

    def setUp(self):
        self.client = TestClient(app)

    # ------------------------------------------------------------------------
    # 1. DISCOVERY & EXTRACTION TESTS
    # ------------------------------------------------------------------------

    def test_extract_discord_invite_only(self):
        """Test extraction when only a Discord server invite is present."""
        text = "Join our community on Discord: https://discord.gg/coolcreator to chat!"
        discord_profile = extract_discord_information(text)

        self.assertIsNotNone(discord_profile)
        self.assertEqual(discord_profile.status, "discovered")
        self.assertIsNone(discord_profile.discord_user_id)
        self.assertEqual(discord_profile.discord_invite, "https://discord.gg/coolcreator")
        self.assertEqual(discord_profile.url, "https://discord.gg/coolcreator")

    def test_extract_discord_user_profile_link(self):
        """Test extraction when a direct Discord user link with a snowflake is present."""
        text = "Message me directly: https://discord.com/users/803511102246789123 for collabs."
        discord_profile = extract_discord_information(text)

        self.assertIsNotNone(discord_profile)
        self.assertEqual(discord_profile.status, "sendable")
        self.assertEqual(discord_profile.discord_user_id, "803511102246789123")
        self.assertEqual(discord_profile.url, "https://discord.com/users/803511102246789123")

    def test_extract_discord_user_id_text_pattern(self):
        """Test extraction when Discord User ID is explicitly written in text."""
        text = "For business outreach: Discord User ID: 104523981726354129 or email me."
        discord_profile = extract_discord_information(text)

        self.assertIsNotNone(discord_profile)
        self.assertEqual(discord_profile.status, "sendable")
        self.assertEqual(discord_profile.discord_user_id, "104523981726354129")

    def test_extract_discord_username_handle(self):
        """Test extraction when only a username handle is found (not a snowflake ID)."""
        text = "Contact me on Discord: creator_pro for any sponsorships."
        discord_profile = extract_discord_information(text)

        self.assertIsNotNone(discord_profile)
        self.assertEqual(discord_profile.status, "discovered")
        self.assertIsNone(discord_profile.discord_user_id)
        self.assertEqual(discord_profile.discord_username, "creator_pro")

    def test_social_profiles_list_includes_discord_details(self):
        """Test that extract_social_profiles populates Discord details on SocialProfile."""
        text = "Discord: https://discord.com/users/987654321098765432 and IG: instagram.com/creators"
        socials = extract_social_profiles(text)
        discord_sp = next((s for s in socials if s.platform == "Discord"), None)

        self.assertIsNotNone(discord_sp)
        self.assertEqual(discord_sp.status, "sendable")
        self.assertEqual(discord_sp.discord_user_id, "987654321098765432")

    def test_extract_discord_invite_with_excluded_word_vanity(self):
        """Test that invite links with vanity names like 'community', 'server', 'chat' are not rejected."""
        text = "Join our official community: https://discord.gg/community or https://discord.gg/server"
        discord_profile = extract_discord_information(text)

        self.assertIsNotNone(discord_profile)
        self.assertEqual(discord_profile.status, "discovered")
        self.assertIn("discord.gg/", discord_profile.discord_invite)

        socials = extract_social_profiles(text)
        disc_socials = [s for s in socials if s.platform == "Discord"]
        self.assertGreaterEqual(len(disc_socials), 1)
        self.assertTrue(any(s.discord_invite for s in disc_socials))

    def test_extract_discord_various_domains(self):
        """Test extraction across discordapp.com, discord.io, discord.me, and discord.com/servers."""
        domains_and_links = [
            ("https://discordapp.com/invite/creative-hub", "creative-hub"),
            ("https://discord.io/mrbeast", "mrbeast"),
            ("https://discord.me/progamers", "progamers"),
            ("https://discord.com/servers/community-guild-1234", "community-guild-1234"),
        ]
        for link, expected_code in domains_and_links:
            text = f"Check out our Discord: {link} to talk!"
            info = extract_discord_information(text)
            self.assertIsNotNone(info, f"Failed for {link}")
            self.assertEqual(info.discord_invite, f"https://discord.gg/{expected_code}")

            socials = extract_social_profiles(text)
            disc = next((s for s in socials if s.platform == "Discord"), None)
            self.assertIsNotNone(disc, f"extract_social_profiles failed for {link}")
            self.assertEqual(disc.discord_invite, f"https://discord.gg/{expected_code}")

    # ------------------------------------------------------------------------
    # 2. SNOWFLAKE VALIDATION TESTS
    # ------------------------------------------------------------------------

    def test_validate_snowflake(self):
        """Test snowflake format validation (17-20 digits)."""
        # Valid snowflakes
        self.assertTrue(validate_snowflake("803511102246789123"))     # 18 digits
        self.assertTrue(validate_snowflake("12345678901234567"))      # 17 digits
        self.assertTrue(validate_snowflake("12345678901234567890"))   # 20 digits

        # Invalid snowflakes
        self.assertFalse(validate_snowflake(""))
        self.assertFalse(validate_snowflake("12345"))                 # too short
        self.assertFalse(validate_snowflake("123456789012345678901")) # too long (21 digits)
        self.assertFalse(validate_snowflake("username_here"))         # alpha
        self.assertFalse(validate_snowflake("80351110224678912a"))    # contains letter
        self.assertFalse(validate_snowflake(None))

    # ------------------------------------------------------------------------
    # 3. DISCORD SERVICE UNIT TESTS
    # ------------------------------------------------------------------------

    async def test_discord_service_missing_token(self):
        """Test error raised when DISCORD_BOT_TOKEN is not configured."""
        with patch.object(Settings, "get_discord_bot_token", return_value=""):
            with self.assertRaises(DiscordConfigurationError):
                await send_dm_message("803511102246789123", "Hello creator")

    async def test_discord_service_invalid_snowflake_raises(self):
        """Test error raised when invalid recipient ID is provided."""
        with self.assertRaises(DiscordValidationError):
            await send_dm_message("invalid_user_id", "Hello creator")

    async def test_verify_bot_connection_success(self):
        """Test bot connection verification on 200 OK."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "111222333444555666",
            "username": "ArclentBot",
            "discriminator": "0"
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch.object(Settings, "get_discord_bot_token", return_value="dummy_bot_token"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await verify_bot_connection()
                self.assertTrue(result["valid"])
                self.assertEqual(result["username"], "ArclentBot")
                self.assertEqual(result["bot_id"], "111222333444555666")

    async def test_verify_bot_connection_unauthorized(self):
        """Test bot connection verification on 401 Unauthorized."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"message": "401: Unauthorized", "code": 0}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch.object(Settings, "get_discord_bot_token", return_value="invalid_bot_token"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with self.assertRaises(DiscordAuthenticationError):
                    await verify_bot_connection()

    async def test_send_dm_message_success(self):
        """Test successful DM creation and message dispatch."""
        # 1st call: create DM channel (POST /users/@me/channels)
        dm_resp = MagicMock()
        dm_resp.status_code = 200
        dm_resp.json.return_value = {"id": "999888777666555444"}

        # 2nd call: send message (POST /channels/{channel_id}/messages)
        msg_resp = MagicMock()
        msg_resp.status_code = 200
        msg_resp.json.return_value = {
            "id": "777666555444333222",
            "channel_id": "999888777666555444",
            "content": "Hello creator!",
            "timestamp": "2026-09-12T10:30:00Z"
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = [dm_resp, msg_resp]

        with patch.object(Settings, "get_discord_bot_token", return_value="valid_bot_token"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await send_dm_message("803511102246789123", "Hello creator!")
                self.assertTrue(result["success"])
                self.assertEqual(result["message_id"], "777666555444333222")
                self.assertEqual(result["channel_id"], "999888777666555444")
                self.assertEqual(result["recipient_id"], "803511102246789123")

    async def test_send_dm_message_delivery_error_50007(self):
        """Test Discord error 50007 ('Cannot send messages to this user') is cleanly mapped."""
        dm_resp = MagicMock()
        dm_resp.status_code = 200
        dm_resp.json.return_value = {"id": "999888777666555444"}

        msg_resp = MagicMock()
        msg_resp.status_code = 403
        msg_resp.json.return_value = {
            "message": "Cannot send messages to this user",
            "code": 50007
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.side_effect = [dm_resp, msg_resp]

        with patch.object(Settings, "get_discord_bot_token", return_value="valid_bot_token"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with self.assertRaises(DiscordDeliveryError) as ctx:
                    await send_dm_message("803511102246789123", "Hello creator!")
                
                self.assertIn("DMs restricted", str(ctx.exception))
                self.assertIn("mutual server", str(ctx.exception))

    # ------------------------------------------------------------------------
    # 4. MESSAGE GENERATOR TEST
    # ------------------------------------------------------------------------

    async def test_generate_outreach_message_discord(self):
        """Test message generation for Discord channel."""
        msg = await generate_outreach_message(
            creator_name="TechReviewHQ",
            channel_name="TechReviewHQ",
            video_title="Top 10 AI Tools of 2026",
            channel="discord",
            user_role="Video editor"
        )

        self.assertEqual(msg.channel, "discord")
        self.assertIsNone(msg.subject)  # Discord DMs have no subject line
        self.assertIn("TechReviewHQ", msg.body)
        self.assertIn("collaborator via Discord", msg.body)

    # ------------------------------------------------------------------------
    # 5. API ENDPOINT TESTS
    # ------------------------------------------------------------------------

    @patch("app.api.outreach.discord_service.send_dm_message", new_callable=AsyncMock)
    def test_api_send_discord_message_success(self, mock_send_dm):
        """Test POST /api/outreach/send-discord-message end-to-end success."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        session.creator = CreatorProfile(name="GamerZone", channel_name="GamerZone")
        session.discord_profile = DiscordProfile(
            status="sendable",
            discord_user_id="803511102246789123"
        )

        mock_send_dm.return_value = {
            "success": True,
            "message_id": "999000111222333444",
            "channel_id": "888111222333444555",
            "recipient_id": "803511102246789123",
            "sent_at": "2026-09-12T10:30:00Z"
        }

        payload = {
            "session_id": session.session_id,
            "discord_user_id": "803511102246789123",
            "message": "Hey GamerZone, loved your latest clip! Would love to partner on Discord."
        }

        response = self.client.post("/api/outreach/send-discord-message", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message_id"], "999000111222333444")
        self.assertEqual(data["recipient_id"], "803511102246789123")
        self.assertEqual(data["status"], "sent")

        # Check session update
        updated_session = get_session(session.session_id)
        self.assertEqual(updated_session.selected_channel, "discord")
        self.assertEqual(updated_session.stage, OutreachStage.SENT)
        self.assertEqual(updated_session.discord_message_id, "999000111222333444")
        
        # Verify verification URL was embedded in the message sent by bot
        sent_message = mock_send_dm.call_args.kwargs["message"]
        self.assertIn(f"/verify?session_id={session.session_id}", sent_message)

    @patch("app.api.outreach.discord_service.send_dm_message", new_callable=AsyncMock)
    def test_api_send_discord_message_delivery_failure_403(self, mock_send_dm):
        """Test POST /api/outreach/send-discord-message handles 403 / 50007 correctly."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        mock_send_dm.side_effect = DiscordDeliveryError(
            "We couldn't send the Discord message. The creator may have Discord DMs restricted or does not share a mutual server with the Arclent bot. Try another contact method."
        )

        payload = {
            "session_id": session.session_id,
            "discord_user_id": "803511102246789123",
            "message": "Hey there!"
        }

        response = self.client.post("/api/outreach/send-discord-message", json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertIn("DMs restricted", response.json()["detail"])

    def test_api_send_discord_message_invalid_snowflake(self):
        """Test POST /api/outreach/send-discord-message rejects invalid recipient ID."""
        session = create_session("https://www.youtube.com/watch?v=0e3GPea1Tyg")
        payload = {
            "session_id": session.session_id,
            "discord_user_id": "not-a-snowflake",
            "message": "Hello!"
        }

        response = self.client.post("/api/outreach/send-discord-message", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("17-20 digit numeric snowflake", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
