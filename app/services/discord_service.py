"""Official Discord Bot Service for direct messaging outreach.

Uses the official Discord REST API v10 to:
1. Validate Discord recipient IDs (17-20 digit numeric snowflakes)
2. Create or retrieve direct message (DM) channels via POST /users/@me/channels
3. Dispatch outreach messages via POST /channels/{channel_id}/messages
4. Return message ID and delivery status
5. Provide secure and friendly error handling without exposing bot tokens.
"""

import re
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
