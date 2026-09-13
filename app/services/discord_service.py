"""Official Discord Bot Service for direct messaging outreach.

Uses the official Discord REST API v10 to:
1. Validate Discord recipient IDs (17-20 digit numeric snowflakes)
2. Create or retrieve direct message (DM) channels via POST /users/@me/channels
3. Dispatch outreach messages via POST /channels/{channel_id}/messages
4. Return message ID and delivery status
5. Provide secure and friendly error handling without exposing bot tokens.
"""

import re
import urllib.parse
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
SNOWFLAKE_REGEX = re.compile(r"^[0-9]{17,20}$")
MAX_DISCORD_MESSAGE_LENGTH = 2000


class DiscordServiceError(Exception):
    """Base exception for Discord service errors."""
    def __init__(self, message: str, status_code: int = 400, discord_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.discord_code = discord_code


class DiscordConfigurationError(DiscordServiceError):
    """Raised when DISCORD_BOT_TOKEN is missing or improperly configured."""
    def __init__(self, message: str = "Discord Bot Token is not configured. Please set DISCORD_BOT_TOKEN in your .env file."):
        super().__init__(message, status_code=500)


class DiscordValidationError(DiscordServiceError):
    """Raised when a recipient Discord user ID is invalid."""
    def __init__(self, message: str = "Invalid Discord User ID. A Discord User ID must be a 17-20 digit numeric snowflake."):
        super().__init__(message, status_code=400)


class DiscordAuthenticationError(DiscordServiceError):
    """Raised when Discord returns 401 Unauthorized."""
    def __init__(self, message: str = "Discord Bot authorization failed. Please check DISCORD_BOT_TOKEN in the Discord Developer Portal."):
        super().__init__(message, status_code=401)


class DiscordDeliveryError(DiscordServiceError):
    """Raised when Discord returns 403 Forbidden (e.g. DMs closed, no mutual guild)."""
    def __init__(self, message: str = "We couldn't send the Discord message. The creator may have Discord DMs restricted or does not share a mutual server with the Arclent bot. Try another contact method.", discord_code: Optional[int] = None):
        super().__init__(message, status_code=403, discord_code=discord_code)


class DiscordNotFoundError(DiscordServiceError):
    """Raised when Discord user or channel is not found (404)."""
    def __init__(self, message: str = "Discord user not found. The provided Discord User ID does not exist."):
        super().__init__(message, status_code=404)


class DiscordRateLimitError(DiscordServiceError):
    """Raised when Discord rate limit is exceeded (429)."""
    def __init__(self, message: str = "Discord rate limit reached. Please wait a moment before trying again."):
        super().__init__(message, status_code=429)


class DiscordNetworkError(DiscordServiceError):
    """Raised on connection timeout or network failure."""
    def __init__(self, message: str = "Network timeout connecting to Discord API. Please retry."):
        super().__init__(message, status_code=504)


class DiscordInviteResolutionError(DiscordServiceError):
    """Raised when an invite cannot be resolved to an active Discord server."""
    def __init__(self, message: str = "Could not resolve invite to a Discord server. The invite may be expired or invalid.", discord_code: Optional[int] = None):
        super().__init__(message, status_code=404, discord_code=discord_code)


class DiscordBotNotInServerError(DiscordServiceError):
    """Raised when the Arclent bot is not present in the target Discord server."""
    def __init__(self, message: str = "Arclent Bot is not in the target Discord server. Please install the bot to that server first.", discord_code: Optional[int] = None):
        super().__init__(message, status_code=404, discord_code=discord_code)


class DiscordBotAccessError(DiscordServiceError):
    """Raised when the Arclent bot lacks permission to inspect members in the server."""
    def __init__(self, message: str = "Arclent Bot lacks permission to access server members in the target Discord server.", discord_code: Optional[int] = None):
        super().__init__(message, status_code=403, discord_code=discord_code)


class DiscordOAuthError(DiscordServiceError):
    """Raised when Discord OAuth authorization or token exchange fails."""
    def __init__(self, message: str = "Discord OAuth authentication failed. Please try logging in again.", status_code: int = 400, discord_code: Optional[int] = None):
        super().__init__(message, status_code=status_code, discord_code=discord_code)



def validate_snowflake(user_id: str) -> bool:
    """Validate that a string represents a valid Discord snowflake ID (17-20 digits)."""
    if not user_id or not isinstance(user_id, str):
        return False
    return bool(SNOWFLAKE_REGEX.match(user_id.strip()))


def get_discord_headers() -> Dict[str, str]:
    """Construct sanitized HTTP headers for official Discord Bot REST API."""
    token = settings.get_discord_bot_token()
    if not token:
        raise DiscordConfigurationError()
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "ArclentDiscordBot (https://arclent.com, 1.0)"
    }


async def verify_bot_connection() -> Dict[str, Any]:
    """Verify that the configured bot token is valid and retrieve bot user info."""
    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/users/@me"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 401:
                logger.error("Discord bot token authentication failed (401)")
                raise DiscordAuthenticationError()
            resp.raise_for_status()
            data = resp.json()
            return {
                "valid": True,
                "bot_id": data.get("id"),
                "username": data.get("username"),
                "discriminator": data.get("discriminator")
            }
    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Failed to verify Discord bot token: {e}", exc_info=True)
        raise DiscordServiceError(f"Could not connect to Discord API: {str(e)}")


async def create_dm_channel(recipient_id: str) -> str:
    """Create or retrieve a direct message (DM) channel with the given recipient snowflake ID.
    
    API: POST https://discord.com/api/v10/users/@me/channels
    Payload: {"recipient_id": "<recipient_id>"}
    Returns: DM channel ID (string)
    """
    clean_id = (recipient_id or "").strip()
    if not validate_snowflake(clean_id):
        raise DiscordValidationError(f"Invalid recipient Discord ID '{clean_id}'. Must be a 17-20 digit numeric snowflake.")

    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/users/@me/channels"
    payload = {"recipient_id": clean_id}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            status = resp.status_code
            
            if status == 200 or status == 201:
                data = resp.json()
                channel_id = data.get("id")
                if not channel_id:
                    raise DiscordServiceError("Discord API did not return a valid channel ID.")
                return str(channel_id)

            # Handle errors cleanly
            try:
                err_json = resp.json()
            except Exception:
                err_json = {}
            
            discord_code = err_json.get("code")
            logger.warning(f"Discord create DM failed (HTTP {status}, code {discord_code}): {err_json.get('message')}")

            if status == 401:
                raise DiscordAuthenticationError()
            elif status == 403:
                # 50007 = Cannot send messages to this user
                raise DiscordDeliveryError(
                    message="We couldn't send the Discord message. The creator may have Discord DMs restricted or does not share a mutual server with the Arclent bot. Try another contact method.",
                    discord_code=discord_code
                )
            elif status == 404:
                raise DiscordNotFoundError(f"Discord user '{clean_id}' does not exist.")
            elif status == 429:
                raise DiscordRateLimitError()
            else:
                raw_msg = err_json.get("message") or resp.text or "Unknown Discord API error"
                raise DiscordServiceError(f"Discord API error: {raw_msg}", status_code=status, discord_code=discord_code)

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error creating DM channel for user {clean_id}: {e}", exc_info=True)
        raise DiscordServiceError("Failed to initiate direct message with creator. Please verify the Discord ID.")


async def send_dm_message(recipient_id: str, message: str) -> Dict[str, Any]:
    """Send an outreach message directly to a creator via the Arclent Discord Bot.
    
    Steps:
    1. Validate recipient ID snowflake
    2. Validate and trim message if needed (2000 char Discord limit)
    3. Open or retrieve the DM channel
    4. Dispatch the message via POST /channels/{channel_id}/messages
    5. Return structured confirmation with message ID
    """
    clean_id = (recipient_id or "").strip()
    if not validate_snowflake(clean_id):
        raise DiscordValidationError(f"Invalid recipient Discord ID '{clean_id}'. Must be a 17-20 digit numeric snowflake.")

    msg_content = (message or "").strip()
    if not msg_content:
        raise DiscordValidationError("Outreach message content cannot be empty.")

    if len(msg_content) > MAX_DISCORD_MESSAGE_LENGTH:
        logger.warning(f"Discord message exceeds {MAX_DISCORD_MESSAGE_LENGTH} characters. Truncating.")
        msg_content = msg_content[:MAX_DISCORD_MESSAGE_LENGTH - 3] + "..."

    # Step 1: Open DM channel
    channel_id = await create_dm_channel(clean_id)

    # Step 2: Send Message to channel
    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    payload = {"content": msg_content}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            status = resp.status_code

            if status == 200 or status == 201:
                data = resp.json()
                msg_id = data.get("id")
                sent_timestamp = data.get("timestamp") or datetime.now(timezone.utc).isoformat()
                logger.info(f"Successfully dispatched Discord message {msg_id} to recipient {clean_id}")
                return {
                    "success": True,
                    "platform": "discord",
                    "status": "sent",
                    "message_id": str(msg_id) if msg_id else None,
                    "recipient_id": clean_id,
                    "channel_id": channel_id,
                    "sent_at": sent_timestamp
                }

            try:
                err_json = resp.json()
            except Exception:
                err_json = {}

            discord_code = err_json.get("code")
            logger.warning(f"Discord send message failed (HTTP {status}, code {discord_code}): {err_json.get('message')}")

            if status == 401:
                raise DiscordAuthenticationError()
            elif status == 403:
                raise DiscordDeliveryError(
                    message="We couldn't send the Discord message. The creator may have Discord DMs restricted or does not share a mutual server with the Arclent bot. Try another contact method.",
                    discord_code=discord_code
                )
            elif status == 404:
                raise DiscordNotFoundError("The target Discord channel was not found.")
            elif status == 429:
                raise DiscordRateLimitError()
            else:
                raw_msg = err_json.get("message") or resp.text or "Unknown Discord API error"
                raise DiscordServiceError(f"Discord API error: {raw_msg}", status_code=status, discord_code=discord_code)

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error dispatching message to recipient {clean_id}: {e}", exc_info=True)
        raise DiscordServiceError("Failed to deliver Discord message. The creator's privacy settings may prevent direct messages.")


def extract_invite_code(invite_url_or_code: str) -> Optional[str]:
    """Extract clean Discord invite code from a URL or raw code.
    
    Supports:
    - https://discord.gg/xxxxx
    - https://discord.com/invite/xxxxx
    - https://discordapp.com/invite/xxxxx
    - https://discord.io/xxxxx
    - https://discord.me/xxxxx
    - https://discord.com/servers/xxxxx
    - raw invite code (e.g. xxxxx)
    """
    if not invite_url_or_code or not isinstance(invite_url_or_code, str):
        return None
    raw = invite_url_or_code.strip()
    if not raw:
        return None

    # Remove query string and hash fragments
    if "?" in raw:
        raw = raw.split("?")[0]
    if "#" in raw:
        raw = raw.split("#")[0]

    # Explicitly reject non-invite Discord URL paths (user profiles, channels, etc.)
    lower = raw.lower()
    if "/users/" in lower or "/channels/" in lower or "/guilds/" in lower:
        return None

    # If it contains a slash or protocol, require an explicit invite prefix
    if "/" in raw:
        match = re.search(
            r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg\/|(?:discord\.com|discordapp\.com)\/(?:invite|servers)\/|discord\.io\/|discord\.me\/)([a-zA-Z0-9_\-]{2,40})\/?$",
            raw,
            re.IGNORECASE
        )
        if match:
            code = match.group(1).rstrip("./_…-")
            if len(code) >= 2 and code.lower() not in {"invite", "channels", "users", "login", "register", "app", "api", "oauth2"}:
                return code
        return None

    # If it's a raw code without slashes
    if re.fullmatch(r"[a-zA-Z0-9_\-]{2,40}", raw):
        if raw.lower() not in {"invite", "channels", "users", "login", "register", "app", "api", "oauth2"}:
            return raw

    return None


async def resolve_invite_to_guild(invite_url_or_code: str) -> Dict[str, Any]:
    """Resolve a Discord invite link or code to its target guild/server using official Discord REST API v10.
    
    API: GET https://discord.com/api/v10/invites/{invite_code}
    Returns:
        Dict with guild_id, guild_name, guild_icon, approximate_member_count, and code.
    Raises:
        DiscordInviteResolutionError: If invite cannot be resolved to an active guild.
        DiscordRateLimitError: If Discord rate limit is exceeded.
        DiscordNetworkError: On connection failure.
    """
    code = extract_invite_code(invite_url_or_code)
    if not code:
        raise DiscordInviteResolutionError(f"Invalid or empty Discord invite code: '{invite_url_or_code}'")

    url = f"{DISCORD_API_BASE}/invites/{code}?with_counts=true"
    headers = {
        "User-Agent": "ArclentDiscordBot (https://arclent.com, 1.0)"
    }
    # Pass bot token if configured for higher rate limits
    token = settings.get_discord_bot_token()
    if token:
        headers["Authorization"] = f"Bot {token}"

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url, headers=headers)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                guild = data.get("guild")
                if not guild or not guild.get("id"):
                    raise DiscordInviteResolutionError(f"Invite '{code}' did not contain a valid target server.")

                guild_id = str(guild.get("id"))
                guild_name = str(guild.get("name") or "Discord Server")
                guild_icon = guild.get("icon")
                member_count = data.get("approximate_member_count")

                logger.info(f"Resolved Discord invite '{code}' -> Guild '{guild_name}' (ID: {guild_id})")
                return {
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "guild_icon": guild_icon,
                    "approximate_member_count": member_count,
                    "invite_code": code,
                    "invite_url": f"https://discord.gg/{code}"
                }

            try:
                err_json = resp.json()
            except Exception:
                err_json = {}

            discord_code = err_json.get("code")
            logger.warning(f"Discord resolve invite '{code}' failed (HTTP {status}, code {discord_code}): {err_json.get('message')}")

            if status == 404 or discord_code == 10006:
                raise DiscordInviteResolutionError(
                    message=f"Discord invite '{code}' could not be resolved. The invite link may be expired, deleted, or invalid.",
                    discord_code=discord_code
                )
            elif status == 429:
                raise DiscordRateLimitError()
            else:
                raw_msg = err_json.get("message") or resp.text or "Unknown Discord API error"
                raise DiscordServiceError(f"Discord API error resolving invite: {raw_msg}", status_code=status, discord_code=discord_code)

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error resolving Discord invite '{code}': {e}", exc_info=True)
        raise DiscordServiceError(f"Could not connect to Discord API to resolve invite: {str(e)}")


async def check_guild_membership(guild_id: str, user_id: str) -> Dict[str, Any]:
    """Check whether a Discord User ID is a member of a target Discord guild/server using Arclent Bot.
    
    API: GET https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}
    Requires: Bot installed in guild with appropriate permissions.
    Returns:
        Dict with:
        - is_member: bool (True if member, False if 404 Unknown Member)
        - status: "verified" | "not_verified"
        - user_id: str
        - guild_id: str
        - roles: list of role snowflake strings (if member)
        - joined_at: ISO timestamp (if member)
    Raises:
        DiscordBotNotInServerError: If Arclent Bot is not in target guild (404, code 10004).
        DiscordBotAccessError: If Arclent Bot lacks member access (403, code 50001).
        DiscordRateLimitError: If rate limit is hit (429).
        DiscordAuthenticationError: If bot token is invalid.
    """
    clean_uid = (user_id or "").strip()
    clean_gid = (guild_id or "").strip()

    if not validate_snowflake(clean_uid):
        raise DiscordValidationError(f"Invalid Discord User ID '{clean_uid}'. Must be a 17-20 digit numeric snowflake.")
    if not validate_snowflake(clean_gid):
        raise DiscordValidationError(f"Invalid Discord Guild ID '{clean_gid}'. Must be a 17-20 digit numeric snowflake.")

    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/guilds/{clean_gid}/members/{clean_uid}"

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(url, headers=headers)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                logger.info(f"Verified Discord user {clean_uid} is a member of guild {clean_gid}")
                return {
                    "is_member": True,
                    "status": "verified",
                    "user_id": clean_uid,
                    "guild_id": clean_gid,
                    "roles": data.get("roles", []),
                    "joined_at": data.get("joined_at"),
                    "nick": data.get("nick")
                }

            try:
                err_json = resp.json()
            except Exception:
                err_json = {}

            discord_code = err_json.get("code")
            logger.info(f"Guild membership check response: HTTP {status}, code {discord_code}, user {clean_uid}, guild {clean_gid}")

            # 10007 = Unknown Member -> Not in server
            if status == 404 and discord_code == 10007:
                return {
                    "is_member": False,
                    "status": "not_verified",
                    "user_id": clean_uid,
                    "guild_id": clean_gid,
                    "reason": "user_not_in_guild"
                }

            # 10004 = Unknown Guild -> Bot is not in the server
            if status == 404 and discord_code == 10004:
                raise DiscordBotNotInServerError(
                    message=f"The Arclent bot is not in this Discord server ({clean_gid}). Please invite the bot to the server first.",
                    discord_code=discord_code
                )

            # 50001 = Missing Access -> Bot lacks permission in guild
            if status == 403 and discord_code == 50001:
                raise DiscordBotAccessError(
                    message=f"The Arclent bot lacks permission to access members in Discord server ({clean_gid}).",
                    discord_code=discord_code
                )

            if status == 401:
                raise DiscordAuthenticationError()
            elif status == 429:
                raise DiscordRateLimitError()
            elif status == 404:
                # Generic 404 fallback for member not found
                return {
                    "is_member": False,
                    "status": "not_verified",
                    "user_id": clean_uid,
                    "guild_id": clean_gid,
                    "reason": "member_not_found"
                }
            else:
                raw_msg = err_json.get("message") or resp.text or "Unknown Discord API error"
                raise DiscordServiceError(f"Discord API error checking membership: {raw_msg}", status_code=status, discord_code=discord_code)

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error checking guild membership for user {clean_uid} in guild {clean_gid}: {e}", exc_info=True)
        raise DiscordServiceError(f"Could not check Discord server membership: {str(e)}")


def generate_discord_oauth_url(state: str, prompt: str = "consent") -> str:
    """Generate official Discord OAuth2 authorization URL with minimum required scope 'identify'.
    
    Scope:
    - 'identify': Returns logged-in user profile with Discord snowflake ID (GET /users/@me).
    """
    client_id = settings.get_discord_client_id()
    if not client_id:
        raise DiscordConfigurationError("DISCORD_CLIENT_ID is not configured in .env file.")

    redirect_uri = settings.get_discord_redirect_uri()
    encoded_redirect = urllib.parse.quote(redirect_uri, safe="")
    encoded_state = urllib.parse.quote(state, safe="")

    return (
        f"https://discord.com/oauth2/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={encoded_redirect}"
        f"&scope=identify"
        f"&state={encoded_state}"
        f"&prompt={prompt}"
    )


async def exchange_oauth_code(code: str) -> Dict[str, Any]:
    """Exchange Discord OAuth2 authorization code for an access token.
    
    API: POST https://discord.com/api/v10/oauth2/token
    """
    client_id = settings.get_discord_client_id()
    client_secret = settings.get_discord_client_secret()
    if not client_id or not client_secret:
        raise DiscordConfigurationError("DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET must be configured in .env.")

    redirect_uri = settings.get_discord_redirect_uri()
    url = f"{DISCORD_API_BASE}/oauth2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code.strip(),
        "redirect_uri": redirect_uri
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "ArclentDiscordBot (https://arclent.com, 1.0)"
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(url, data=payload, headers=headers)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                return data

            try:
                err_json = resp.json()
            except Exception:
                err_json = {}

            err_desc = err_json.get("error_description") or err_json.get("message") or resp.text
            logger.warning(f"Discord OAuth token exchange failed (HTTP {status}): {err_desc}")

            if status == 429:
                raise DiscordRateLimitError()
            raise DiscordOAuthError(f"Failed to exchange Discord authorization code: {err_desc}", status_code=status)

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error during Discord OAuth token exchange: {e}", exc_info=True)
        raise DiscordOAuthError(f"OAuth connection error: {str(e)}")


async def get_authenticated_user(access_token: str) -> Dict[str, Any]:
    """Retrieve the authenticated Discord user profile and extract their Discord User ID.
    
    API: GET https://discord.com/api/v10/users/@me
    Returns:
        Dict with 'id' (the Discord User ID snowflake), 'username', 'discriminator', 'global_name', 'avatar'.
    """
    if not access_token:
        raise DiscordOAuthError("Missing Discord access token.")

    url = f"{DISCORD_API_BASE}/users/@me"
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "User-Agent": "ArclentDiscordBot (https://arclent.com, 1.0)"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            status = resp.status_code

            if status == 200:
                data = resp.json()
                user_id = data.get("id")
                if not user_id:
                    raise DiscordOAuthError("Discord API did not return a user ID.")
                logger.info(f"Retrieved authenticated Discord user: id={user_id}, username={data.get('username')}")
                return {
                    "id": str(user_id),
                    "username": data.get("username"),
                    "discriminator": data.get("discriminator"),
                    "global_name": data.get("global_name"),
                    "avatar": data.get("avatar")
                }

            if status == 401:
                raise DiscordAuthenticationError("Discord user access token expired or invalid.")
            elif status == 429:
                raise DiscordRateLimitError()
            else:
                raise DiscordOAuthError(f"Could not retrieve Discord user profile (HTTP {status})")

    except DiscordServiceError:
        raise
    except httpx.TimeoutException:
        raise DiscordNetworkError()
    except Exception as e:
        logger.error(f"Unexpected error retrieving authenticated Discord user: {e}", exc_info=True)
        raise DiscordOAuthError(f"Could not retrieve Discord user: {str(e)}")


async def verify_user_guild_membership_by_invite(invite_url_or_code: str, user_id: str) -> Dict[str, Any]:
    """High-level verification function:
    1. Resolves Discord invite link to guild
    2. Checks whether user_id is a member of that guild
    Returns combined structured result dictionary.
    """
    guild_info = await resolve_invite_to_guild(invite_url_or_code)
    guild_id = guild_info["guild_id"]
    guild_name = guild_info["guild_name"]

    membership = await check_guild_membership(guild_id=guild_id, user_id=user_id)
    membership["guild_name"] = guild_name
    membership["invite_url"] = guild_info.get("invite_url") or invite_url_or_code
    membership["approximate_member_count"] = guild_info.get("approximate_member_count")
    return membership

