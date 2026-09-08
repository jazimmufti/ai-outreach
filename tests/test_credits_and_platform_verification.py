"""Tests for credit mentions verification across platforms and Twitch discovery."""

import unittest
from unittest.mock import patch, AsyncMock
import httpx

from app.services.platform_verifier import (
    check_instagram_exists,
    check_x_exists,
    check_facebook_exists,
    check_twitch_exists,
    check_discord_exists,
    verify_username_on_platforms,
    verify_usernames_across_platforms
)
from app.services.youtube_description_parser import (
    extract_credit_candidates,
    extract_verified_contributor_accounts
)
from app.services.social_discovery import (
    extract_social_profiles,
    clean_social_text,
    discover_credits_social_profiles
)
from app.services.auto_verification import verify_contribution_from_description
from app.services.linked_account import set_dummy_linked_instagram_account, reset_dummy_linked_instagram_account


class TestCreditCandidatesExtraction(unittest.TestCase):
    """Tests for extracting credit handles and roles from YouTube descriptions."""

    def test_editor_credit_mention(self):
        desc = "Special thanks to our editor: @ummer.04 for the amazing video edit!"
        candidates = extract_credit_candidates(desc)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["username"], "ummer.04")
        self.assertEqual(candidates[0]["role"], "editor")

    def test_edited_by_credit_mention(self):
        desc = "Video edited by: @creative_mind\nThumbnail by: @art_designer"
        candidates = extract_credit_candidates(desc)
        usernames = [c["username"] for c in candidates]
        self.assertIn("creative_mind", usernames)
        self.assertIn("art_designer", usernames)

    def test_credits_mention_without_platform(self):
        desc = "Credits: @ummer.04\nMusic by: NoCopyrightSounds"
        candidates = extract_credit_candidates(desc)
        usernames = [c["username"] for c in candidates]
        self.assertIn("ummer.04", usernames)

    def test_vfx_and_thumbnail_credits(self):
        desc = "VFX by @fx_master and thumbnail by @cool_thumb"
        candidates = extract_credit_candidates(desc)
        usernames = [c["username"] for c in candidates]
        self.assertIn("fx_master", usernames)
        self.assertIn("cool_thumb", usernames)

    def test_empty_or_no_credits(self):
        self.assertEqual(extract_credit_candidates(""), [])
        self.assertEqual(extract_credit_candidates("Great video! Check out my shop."), [])


class TestTwitchAndSocialDiscovery(unittest.TestCase):
    """Tests for Twitch URL/mention extraction and HTML redirect cleaning."""

    def test_twitch_url_extraction(self):
        text = "Catch my live streams at https://twitch.tv/ninja or twitch.tv/gamer123"
        profiles = extract_social_profiles(text)
        twitch_profiles = [p for p in profiles if p.platform == "Twitch"]
        self.assertTrue(len(twitch_profiles) >= 2)
        users = [p.username for p in twitch_profiles]
        self.assertIn("ninja", users)
        self.assertIn("gamer123", users)

    def test_twitch_text_mention_extraction(self):
        text = "Twitch: ninja\nTwitch - @pro_player"
        profiles = extract_social_profiles(text)
        twitch_profiles = [p for p in profiles if p.platform == "Twitch"]
        self.assertTrue(len(twitch_profiles) >= 2)
        users = [p.username for p in twitch_profiles]
        self.assertIn("ninja", users)
        self.assertIn("pro_player", users)

    def test_youtube_redirect_with_ampersand_entity(self):
        text = "Follow: https://www.youtube.com/redirect?event=channel_description&amp;redir_token=XYZ&amp;q=https%3A%2F%2Finstagram.com%2Fdudeperfect"
        profiles = extract_social_profiles(text)
        self.assertTrue(any(p.platform == "Instagram" and p.username == "dudeperfect" for p in profiles))


class TestPlatformVerifierMocked(unittest.IsolatedAsyncioTestCase):
    """Unit tests for platform existence verifier with mocked HTTP responses."""

    @patch("httpx.AsyncClient.get")
    async def test_instagram_exists_positive(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><meta property="og:title" content="Ummer (@ummer.04) • Instagram photos"></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_instagram_exists("ummer.04")
        self.assertTrue(exists)

    @patch("httpx.AsyncClient.get")
    async def test_instagram_exists_negative_not_found(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>Page Not Found &bull; Instagram</title></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_instagram_exists("fakeuser_99999999")
        self.assertFalse(exists)

    @patch("httpx.AsyncClient.get")
    async def test_twitch_exists_positive(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>Ninja - Twitch</title></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_twitch_exists("ninja")
        self.assertTrue(exists)

    @patch("httpx.AsyncClient.get")
    async def test_twitch_exists_negative_default_title(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>Twitch</title></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_twitch_exists("fakeuser_99999999")
        self.assertFalse(exists)

    @patch("httpx.AsyncClient.get")
    async def test_x_exists_positive(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>Dude Perfect (@DudePerfect) / X</title></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_x_exists("DudePerfect")
        self.assertTrue(exists)

    @patch("httpx.AsyncClient.get")
    async def test_facebook_exists_positive(self, mock_get):
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>Dude Perfect</title></head></html>'
        mock_get.return_value = mock_resp

        exists = await check_facebook_exists("DudePerfect")
        self.assertTrue(exists)

    @patch("httpx.AsyncClient.get")
    async def test_verify_username_on_platforms(self, mock_get):
        def fake_get(url, **kwargs):
            resp = unittest.mock.MagicMock()
            resp.status_code = 200
            if "instagram.com" in url:
                resp.text = '<meta property="og:title" content="Ummer (@ummer.04)">'
            elif "twitch.tv" in url:
                resp.text = '<title>Twitch</title>'
            elif "x.com" in url:
                resp.text = '<title>NO TITLE</title>'
            elif "facebook.com" in url:
                resp.text = '<title>Facebook</title>'
            elif "discord.com" in url:
                resp.status_code = 404
                resp.text = '{}'
            return resp

        mock_get.side_effect = fake_get

        results = await verify_username_on_platforms("ummer.04")
        self.assertTrue(results["Instagram"])
        self.assertFalse(results["Twitch"])
        self.assertFalse(results["X"])
        self.assertFalse(results["Facebook"])
        self.assertFalse(results["Discord"])


class TestAutoVerificationWithCreditUsername(unittest.TestCase):
    """Tests that 'editor: @ummer.04' auto-verifies when the linked account is ummer.04."""

    def setUp(self):
        reset_dummy_linked_instagram_account()

    def tearDown(self):
        reset_dummy_linked_instagram_account()

    def test_editor_credit_auto_verified(self):
        set_dummy_linked_instagram_account("ummer.04")
        desc = "Thanks to everyone who helped. Editor: @ummer.04 for the fast cuts!"
        res = verify_contribution_from_description(desc)
        self.assertTrue(res.verified)
        self.assertEqual(res.status, "auto_verified")
        self.assertEqual(res.matched_account, "ummer.04")


class TestLinkedPlatformCreditChecks(unittest.IsolatedAsyncioTestCase):
    """Tests verifying that unspecified platform credits assume the user's linked platform."""

    def setUp(self):
        reset_dummy_linked_instagram_account()

    def tearDown(self):
        reset_dummy_linked_instagram_account()

    @patch("app.services.platform_verifier.verify_username_on_platforms")
    async def test_linked_instagram_checks_instagram_only(self, mock_verify):
        mock_verify.return_value = {"Instagram": True, "X": False, "Facebook": False, "Twitch": False, "Discord": False}
        
        # When linked Instagram is active and credit mentions "editor: @ummer.04" without platform
        desc = "Editor: @ummer.04"
        results = await extract_verified_contributor_accounts(desc, linked_account="ummer.04")

        # Must have invoked verify_username_on_platforms with platforms=["Instagram"]
        self.assertTrue(mock_verify.called)
        _, kwargs = mock_verify.call_args
        self.assertEqual(kwargs.get("platforms"), ["Instagram"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["platforms"], ["Instagram"])

    @patch("app.services.platform_verifier.verify_username_on_platforms")
    async def test_linked_x_checks_x_only(self, mock_verify):
        mock_verify.return_value = {"Instagram": False, "X": True, "Facebook": False, "Twitch": False, "Discord": False}
        
        # When linked platform is X and credit mentions "editor: @cool_editor" without platform
        desc = "Editor: @cool_editor"
        results = await extract_verified_contributor_accounts(desc, linked_platform="X", linked_account="cool_editor")

        self.assertTrue(mock_verify.called)
        _, kwargs = mock_verify.call_args
        self.assertEqual(kwargs.get("platforms"), ["X"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["platforms"], ["X"])

    @patch("app.services.platform_verifier.verify_username_on_platforms")
    async def test_specified_platform_in_description_checks_that_platform(self, mock_verify):
        mock_verify.return_value = {"Instagram": False, "X": True, "Facebook": False, "Twitch": False, "Discord": False}
        
        # Even if Instagram is linked, if description explicitly specifies Twitter/X:
        desc = "Editor (Twitter): @twitter_editor"
        results = await extract_verified_contributor_accounts(desc, linked_account="ummer.04")

        self.assertTrue(mock_verify.called)
        _, kwargs = mock_verify.call_args
        self.assertEqual(kwargs.get("platforms"), ["X"])


class TestDeliveryBackToHubHidden(unittest.TestCase):
    """Tests ensuring Back to Hub is hidden when collaboration is confirmed."""

    def test_back_to_hub_button_hidden_by_default(self):
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="btn-back-delivery"', html)
        self.assertIn('class="btn-retro-back hidden"', html)


class TestModalConnectInstagramGuards(unittest.TestCase):
    """Tests ensuring connect Instagram modal only shows during processing when unlinked with credits, and redirects to Instagram login."""

    def test_modal_hidden_and_no_hardcoded_handle(self):
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()
        # Modal must be hidden by default
        self.assertIn('id="modal-connect-instagram" class="modal-backdrop hidden"', html)
        # Default template text must not hardcode @ummer.04
        self.assertNotIn('<strong id="modal-detected-handles-list">@ummer.04</strong>', html)
        self.assertIn('<strong id="modal-detected-handles-list"></strong>', html)
        # IG pill must NOT be in the top header
        self.assertNotIn('id="instagram-status-pill"', html)
        # Connecting must be optional with clear skip action
        self.assertIn('Skip (Verify Manually)', html)
        self.assertIn('Connecting Instagram is optional', html)

    def test_app_js_guards_and_instagram_redirect(self):
        with open("frontend/app.js", "r", encoding="utf-8") as f:
            js = f.read()

        # Guard against first page
        self.assertIn('screens.input && !screens.input.classList.contains("hidden")', js)
        self.assertIn('state.stage === "input"', js)

        # Initial state must be null (not connected initially)
        self.assertIn('linkedInstagramAccount: null', js)

        # Guard: only if user hasn't connected
        self.assertIn('if (state.linkedInstagramAccount)', js)

        # Guard: only if credits are mentioned in the given video
        self.assertIn('cleanHandles.length === 0', js)

        # Redirect to Instagram login page on handle entry
        self.assertIn('window.location.href = "https://www.instagram.com/accounts/login/";', js)


class TestRoleMatchingAndStrictExplicitCredits(unittest.TestCase):
    """Tests that credits are strictly explicit and must match the user's role."""

    def test_role_matching_video_editor_accepts_editor_credits(self):
        desc = "Special thanks to our editor: @ummer.04 for the amazing video edit!"
        candidates = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["username"], "ummer.04")

    def test_role_matching_video_editor_rejects_thumbnail_and_vfx(self):
        desc = "Thumbnail by: @cool_thumb\nVFX by: @fx_wizard"
        # Video editor should NOT match thumbnail or vfx credits
        candidates = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(candidates, [])

    def test_role_matching_thumbnail_designer_accepts_thumbnail_credits(self):
        desc = "Editor: @ummer.04\nThumbnail by: @cool_thumb"
        candidates = extract_credit_candidates(desc, user_role="Thumbnail designer")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["username"], "cool_thumb")

    def test_generic_credits_match_any_user_role(self):
        desc = "Credits: @ummer.04\nContributor: @alex_smith"
        candidates_editor = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(len(candidates_editor), 2)
        candidates_thumb = extract_credit_candidates(desc, user_role="Thumbnail designer")
        self.assertEqual(len(candidates_thumb), 2)

    def test_multiple_contributors_on_single_line(self):
        desc = "Contributors: @john_doe @ummer.04 @alex123"
        candidates = extract_credit_candidates(desc, user_role="Video editor")
        usernames = [c["username"] for c in candidates]
        self.assertIn("john_doe", usernames)
        self.assertIn("ummer.04", usernames)
        self.assertIn("alex123", usernames)


class TestDudePerfectNoCreditsScenario(unittest.TestCase):
    """Tests the exact Dude Perfect scenario where promotional channel links exist but no credits."""

    def setUp(self):
        reset_dummy_linked_instagram_account()

    def tearDown(self):
        reset_dummy_linked_instagram_account()

    def test_dude_perfect_description_extracts_no_credits(self):
        dude_perfect_desc = (
            "Welcome to TPC Southwind for ASGB 7 with the Savannah Bananas! "
            "Use anything but golf clubs and once you use it, you lose it until the bag resets. "
            "BODYARMOR FIT is a crisp, sparkling sports drink that delivers refreshing hydration "
            "and functional energy in a convenient can. Thanks to BA for always keeping us hydrated! "
            "Shout out to TPC Southwind for allowing us to take over the course and do one of our most fun videos! "
            "To learn more about TPC Southwind, Home of the FedEx St. Jude Championship, visit "
            "https://www.fedexchampionship.com/course. \"In A Flash\" Performed by Sam Tinnesz, RAT VIRUS "
            "Courtesy of Showdown Productions, Useful Records and Sony Music Words and Music by Sam Tinnesz, "
            "Brennan Aerts and John Keefe © Only Ginger with a Soul Publishing (SESAC) / Case Ace Publishing (SESAC) / "
            "Buck Irish Music (ASCAP)(adm Nettwerk Music Group Inc) / Beefy Beats Music (adm Sony Music Publishing / "
            "All right reserved. Used by permission. #dudeperfect #asgb #asgbsavannahbananas "
            "NEXT LEVEL STUFF ------------------------------------------- "
            "🎒 NEW Merch - http://bit.ly/dudeperfectmerch "
            "📱 Text YTDUDE to 398294 to keep up with us "
            "🔔 Hit the bell next to Subscribe so you don't miss a video! "
            "📕 Read our NEW Book - \"Operation Trick Shot\" - https://book.dudeperfect.com/ "
            "5 best friends and a panda. Dude Perfect is Tyler Toney, Cody Jones, Garrett Hilbert, "
            "Coby Cotton, and Cory Cotton — best known for trick shots, stereotypes, battles, bottle flips, "
            "ping pong, and all-around competitive fun. If you like sports and comedy, come join the Dude Perfect team! "
            "We pride ourselves on making the absolute best family-friendly entertainment possible. Welcome to the crew. "
            "Business or Media: Dude@DudePerfect.com Go Big and God Bless Pound it 👊🏻 Noggin 🙇🏻♂️ Dude Perfect"
        )
        # Even with channel handles mentioned in metadata or description, no credits are extracted
        candidates = extract_credit_candidates(dude_perfect_desc, user_role="Video editor")
        self.assertEqual(candidates, [])

        # Auto-verification result must have extracted_accounts == []
        res = verify_contribution_from_description(dude_perfect_desc, user_role="Video editor")
        self.assertEqual(res.extracted_accounts, [])
        self.assertFalse(res.verified)

    def test_promotional_handles_not_treated_as_credits(self):
        desc = (
            "Check out my other channels:\n"
            "@dudeperfectoutdoors\n"
            "@dudeperfectgaming\n"
            "@almostathletespodcast\n"
            "@dudeperfectplus\n"
        )
        candidates = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(candidates, [])


class TestPlatformExistenceCandidateFiltering(unittest.IsolatedAsyncioTestCase):
    """Tests ensuring candidate usernames must exist on the platform before being suggested."""

    @patch("app.services.platform_verifier.verify_username_on_platforms")
    async def test_non_existent_username_is_omitted(self, mock_verify):
        # When Instagram check returns False (user does not exist)
        mock_verify.return_value = {
            "Instagram": False, "X": False, "Facebook": False, "Twitch": False, "Discord": False
        }
        desc = "Editor: @nonexistent_user_99999"
        results = await extract_verified_contributor_accounts(
            desc, linked_account="ummer.04", user_role="Video editor"
        )
        self.assertEqual(results, [])

    @patch("app.services.platform_verifier.verify_username_on_platforms")
    async def test_existing_username_is_included(self, mock_verify):
        mock_verify.return_value = {
            "Instagram": True, "X": False, "Facebook": False, "Twitch": False, "Discord": False
        }
        desc = "Editor: @ummer.04"
        results = await extract_verified_contributor_accounts(
            desc, linked_account="ummer.04", user_role="Video editor"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], "ummer.04")
        self.assertIn("Instagram", results[0]["platforms"])


class TestNameFirstAndHumanNameCredits(unittest.IsolatedAsyncioTestCase):
    """Tests for name-first credits (DRNKIE: Thumbnail) and plain human name credits (Edited by Trenton Oliver)."""

    def setUp(self):
        reset_dummy_linked_instagram_account()

    def tearDown(self):
        reset_dummy_linked_instagram_account()

    def test_nerdout_thumbnail_designer_credit(self):
        nerdout_desc = """
DRNKIE: Thumbnail
YouTube: [/ drnkie](https://www.youtube.com/drnkie)
Twitch: [/ drnkie](https://www.twitch.tv/drnkie)
Twitter: [/ drnkie](https://twitter.com/drnkie)

Badogblue: Editor/Gameplay
YouTube: [/ badogblue](https://www.youtube.com/user/badogblue)
Twitter: [/ badogblue](https://twitter.com/badogblue)
        """
        # When user selects Thumbnail designer
        candidates_thumb = extract_credit_candidates(nerdout_desc, user_role="Thumbnail designer")
        self.assertEqual(len(candidates_thumb), 1)
        self.assertEqual(candidates_thumb[0]["username"], "drnkie")
        self.assertEqual(candidates_thumb[0]["display_name"], "DRNKIE")
        self.assertIn("Twitter", candidates_thumb[0]["known_platforms"])

        # When user selects Video editor
        candidates_editor = extract_credit_candidates(nerdout_desc, user_role="Video editor")
        self.assertEqual(len(candidates_editor), 1)
        self.assertEqual(candidates_editor[0]["username"], "badogblue")
        self.assertEqual(candidates_editor[0]["display_name"], "Badogblue")

    def test_plain_name_edited_by_trenton_oliver(self):
        desc = "Edited by Trenton Oliver\nHope everyone enjoyed the video!"
        candidates = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["display_name"], "Trenton Oliver")
        self.assertTrue(candidates[0]["is_name"])

        # Auto-verification with linked account 'trenton_oliver'
        res = verify_contribution_from_description(desc, linked_account="trenton_oliver", user_role="Video editor")
        self.assertTrue(res.verified)
        self.assertEqual(res.status, "auto_verified")
        self.assertEqual(res.matched_account, "trenton_oliver")

        # Auto-verification with linked account 'trentonoliver'
        res2 = verify_contribution_from_description(desc, linked_account="trentonoliver", user_role="Video editor")
        self.assertTrue(res2.verified)
        self.assertEqual(res2.status, "auto_verified")

    def test_plain_name_thumbnail_by_trenton_oliver(self):
        desc = "Thumbnail by Trenton Oliver\nGreat match!"
        candidates = extract_credit_candidates(desc, user_role="Thumbnail designer")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["display_name"], "Trenton Oliver")

        # Video editor should not match thumbnail credit
        editor_cand = extract_credit_candidates(desc, user_role="Video editor")
        self.assertEqual(editor_cand, [])


if __name__ == "__main__":
    unittest.main()

