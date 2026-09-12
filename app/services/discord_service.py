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
import urllib.parse
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx

from app.config import settings
from app.models.schemas import DiscordProfile

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
        raise DiscordServiceError("Failed to deliver Discord message. The creator's privacy settings may prevent direct messages.")


def extract_invite_code(invite_str: str) -> Optional[str]:
    """Extract clean Discord invite code from a URL or raw code string."""
    if not invite_str or not isinstance(invite_str, str):
        return None
    raw = invite_str.strip()
    match = re.search(
        r"(?:discord(?:\.gg|\.com\/invite|\.com\/servers|\.io|\.me)|discordapp\.com\/invite)\/([a-zA-Z0-9_\-]{2,40})",
        raw,
        re.IGNORECASE
    )
    if match:
        return match.group(1).rstrip("./_…-")
    clean_raw = raw.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-")
    if re.match(r"^[a-zA-Z0-9_\-]{2,40}$", clean_raw) and clean_raw.lower() not in {"users", "channels", "invite"}:
        return clean_raw
    return None


async def resolve_discord_invite(invite_code_or_url: str) -> Optional[Dict[str, Any]]:
    """Resolve a Discord invite code using official Discord REST API v10.
    
    API: GET https://discord.com/api/v10/invites/{code}?with_counts=true
    Returns: Dict containing guild object, channel, inviter, member counts, or None if invalid/expired.
    """
    code = extract_invite_code(invite_code_or_url)
    if not code:
        return None

    url = f"{DISCORD_API_BASE}/invites/{code}?with_counts=true"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ArclentDiscordBot (https://arclent.com, 1.0)"
    }
    token = settings.get_discord_bot_token()
    if token:
        headers["Authorization"] = f"Bot {token}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"Successfully resolved Discord invite '{code}' -> guild '{data.get('guild', {}).get('name')}'")
                return data
            elif resp.status_code == 404:
                logger.info(f"Discord invite code '{code}' not found or expired (HTTP 404).")
                return None
            else:
                logger.warning(f"Discord invite resolve returned HTTP {resp.status_code} for code '{code}'.")
                return None
    except Exception as e:
        logger.warning(f"Failed to resolve Discord invite '{code}': {e}")
        return None


async def check_bot_in_guild(guild_id: str) -> Optional[Dict[str, Any]]:
    """Check whether the Arclent Discord Bot is a member of the specified guild.
    
    API: GET https://discord.com/api/v10/guilds/{guild_id}
    Returns: Guild object dict if bot is in the server (HTTP 200), or None if bot is absent (403/404).
    """
    if not validate_snowflake(guild_id):
        return None
    token = settings.get_discord_bot_token()
    if not token:
        return None

    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            # 403 (Missing Access) or 404 (Unknown Guild) means bot is not in the guild
            return None
    except Exception as e:
        logger.warning(f"Note checking bot in guild {guild_id}: {e}")
        return None


async def get_guild_member(guild_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch specific guild member details (username, nickname, roles).
    
    API: GET https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}
    """
    if not validate_snowflake(guild_id) or not validate_snowflake(user_id):
        return None
    token = settings.get_discord_bot_token()
    if not token:
        return None

    headers = get_discord_headers()
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.debug(f"Failed to fetch guild member {user_id} in {guild_id}: {e}")
        return None


async def search_guild_members(guild_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search guild members matching a query string.
    
    API: GET https://discord.com/api/v10/guilds/{guild_id}/members/search?query={query}&limit={limit}
    """
    clean_q = (query or "").strip()
    if not clean_q or not validate_snowflake(guild_id):
        return []
    token = settings.get_discord_bot_token()
    if not token:
        return []

    headers = get_discord_headers()
    encoded_q = urllib.parse.quote(clean_q)
    url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members/search?query={encoded_q}&limit={limit}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else []
            return []
    except Exception as e:
        logger.debug(f"Failed to search members in guild {guild_id} with query '{clean_q}': {e}")
        return []


def get_bot_client_id() -> str:
    """Get the Discord Application/Client ID from settings or decode from token."""
    cid = settings.get_discord_client_id()
    if cid:
        return cid
    token = settings.get_discord_bot_token()
    if token and "." in token:
        try:
            import base64
            segment = token.split(".")[0]
            segment += "=" * ((4 - len(segment) % 4) % 4)
            decoded = base64.b64decode(segment).decode("utf-8")
            if decoded.isdigit():
                return decoded
        except Exception:
            pass
    return "1548199535891972136"


def generate_bot_invite_url(guild_id: Optional[str] = None) -> str:
    """Generate the official OAuth2 authorization link to invite the Arclent bot to a server.
    
    If guild_id is provided, includes &guild_id={guild_id} to pre-select the server in Discord's authorization dialog.
    Permissions 274878024704 covers: View Channels, Send Messages, Read Message History, Embed Links.
    """
    client_id = get_bot_client_id()
    base_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=274878024704&scope=bot%20applications.commands"
    if guild_id and str(guild_id).strip():
        base_url += f"&guild_id={str(guild_id).strip()}"
    return base_url


async def discover_creator_in_server(
    invite_code_or_url: str,
    creator_name: str = "",
    channel_name: str = "",
    channel_handle: str = ""
) -> DiscordProfile:
    """Discover Discord server details and attempt to identify the creator's user ID.
    
    Adheres strictly to official Discord REST API v10 and policy constraints:
    - Never uses self-bots or automated user accounts.
    - Resolves the invite via GET /invites/{code}?with_counts=true.
    - Checks whether the Arclent bot is a member via GET /guilds/{guild_id}.
    - If bot is in server, identifies creator from guild owner or member search.
    - If bot is not in server or creator cannot be identified, returns a clear fallback status.
    """
    code = extract_invite_code(invite_code_or_url)
    invite_url = f"https://discord.gg/{code}" if code else (invite_code_or_url or "https://discord.com")

    if not code:
        return DiscordProfile(
            discord_invite=invite_url,
            status="discovered",
            discovery_status="invalid_invite",
            discovery_note="Invalid Discord invite format.",
            url=invite_url
        )

    # 1. Resolve invite code to guild details
    resolved = await resolve_discord_invite(code)
    if not resolved:
        return DiscordProfile(
            discord_invite=invite_url,
            status="discovered",
            discovery_status="invalid_invite",
            discovery_note=f"Discord invite 'discord.gg/{code}' could not be resolved or has expired.",
            url=invite_url
        )

    guild = resolved.get("guild") or {}
    guild_id = str(guild.get("id")) if guild.get("id") else None
    guild_name = guild.get("name") or "Discord Server"
    guild_icon = guild.get("icon")
    member_count = resolved.get("approximate_member_count")
    inviter = resolved.get("inviter") or {}
    bot_invite = generate_bot_invite_url(guild_id)

    # 2. Check bot token configuration
    token = settings.get_discord_bot_token()
    if not token:
        return DiscordProfile(
            discord_invite=invite_url,
            guild_id=guild_id,
            guild_name=guild_name,
            guild_icon=guild_icon,
            approximate_member_count=member_count,
            bot_in_guild=False,
            status="discovered",
            discovery_status="bot_unconfigured",
            discovery_note=f"Discord server '{guild_name}' was resolved, but Arclent Bot token is not configured on this instance. Enter User ID manually.",
            url=invite_url,
            bot_invite_url=bot_invite
        )

    if not guild_id:
        return DiscordProfile(
            discord_invite=invite_url,
            guild_name=guild_name,
            status="discovered",
            discovery_status="server_resolved",
            discovery_note=f"Resolved Discord server '{guild_name}'.",
            url=invite_url,
            bot_invite_url=bot_invite
        )

    # 3. Check whether Arclent Bot is already in this server
    guild_details = await check_bot_in_guild(guild_id)
    if not guild_details:
        # Bot is NOT in the server -> clear fallback without faking
        logger.info(f"Arclent Bot is not in Discord server '{guild_name}' ({guild_id})")
        return DiscordProfile(
            discord_invite=invite_url,
            guild_id=guild_id,
            guild_name=guild_name,
            guild_icon=guild_icon,
            approximate_member_count=member_count,
            bot_in_guild=False,
            status="discovered",
            discovery_status="bot_not_in_server",
            discovery_note=f"Discord server '{guild_name}' was resolved, but Arclent Bot is not in this server. Click 'Add Bot to Server' to authorize it, or enter the creator's User ID manually.",
            url=invite_url,
            bot_invite_url=bot_invite
        )

    # 4. Bot IS in the server -> inspect owner & search members
    logger.info(f"Arclent Bot confirmed in Discord server '{guild_name}' ({guild_id})")
    owner_id = str(guild_details.get("owner_id")) if guild_details.get("owner_id") else None
    owner_member = await get_guild_member(guild_id, owner_id) if owner_id else None
    owner_user = (owner_member.get("user") if owner_member else {}) or {}
    owner_username = owner_user.get("username") or (owner_member.get("nick") if owner_member else None)
    owner_global = owner_user.get("global_name") or ""

    c_candidates = [creator_name, channel_name, channel_handle]
    clean_names = [re.sub(r'[^a-z0-9]', '', c.lower()) for c in c_candidates if c]
    owner_text = re.sub(r'[^a-z0-9]', '', f"{owner_username or ''} {owner_global}".lower())
    clean_gname = re.sub(r'[^a-z0-9]', '', guild_name.lower())

    is_owner_match = False
    if clean_names and any(cn in owner_text or owner_text in cn for cn in clean_names if len(cn) >= 3):
        is_owner_match = True
    elif clean_names and any(cn in clean_gname for cn in clean_names if len(cn) >= 3):
        is_owner_match = True
    elif owner_username and not clean_names:
        is_owner_match = True

    if is_owner_match and owner_id and owner_username:
        return DiscordProfile(
            discord_invite=invite_url,
            discord_username=owner_username,
            discord_user_id=owner_id,
            guild_id=guild_id,
            guild_name=guild_name,
            guild_icon=guild_icon,
            approximate_member_count=member_count,
            bot_in_guild=True,
            status="sendable",
            discovery_status="identified",
            discovery_note=f"Identified server owner @{owner_username} as creator in '{guild_name}'.",
            url=f"https://discord.com/users/{owner_id}",
            bot_invite_url=bot_invite
        )

    # 5. Check if inviter is the creator
    inviter_id = str(inviter.get("id")) if inviter.get("id") else None
    inviter_username = inviter.get("username")
    if inviter_id and inviter_username and clean_names:
        inv_text = re.sub(r'[^a-z0-9]', '', f"{inviter_username} {inviter.get('global_name', '')}".lower())
        if any(cn in inv_text or inv_text in cn for cn in clean_names if len(cn) >= 3):
            return DiscordProfile(
                discord_invite=invite_url,
                discord_username=inviter_username,
                discord_user_id=inviter_id,
                guild_id=guild_id,
                guild_name=guild_name,
                guild_icon=guild_icon,
                approximate_member_count=member_count,
                bot_in_guild=True,
                status="sendable",
                discovery_status="identified",
                discovery_note=f"Identified invite creator @{inviter_username} matching {creator_name or 'channel'} in '{guild_name}'.",
                url=f"https://discord.com/users/{inviter_id}",
                bot_invite_url=bot_invite
            )

    # 6. Search guild members
    for c_cand in c_candidates:
        clean_cand = c_cand.replace("@", "").strip()
        if len(clean_cand) >= 3:
            search_results = await search_guild_members(guild_id, clean_cand, limit=3)
            for m in search_results:
                m_user = m.get("user") or {}
                m_id = str(m_user.get("id")) if m_user.get("id") else None
                m_name = m_user.get("username") or m.get("nick")
                if m_id and m_name:
                    return DiscordProfile(
                        discord_invite=invite_url,
                        discord_username=m_name,
                        discord_user_id=m_id,
                        guild_id=guild_id,
                        guild_name=guild_name,
                        guild_icon=guild_icon,
                        approximate_member_count=member_count,
                        bot_in_guild=True,
                        status="sendable",
                        discovery_status="identified",
                        discovery_note=f"Identified member @{m_name} matching '{c_cand}' in '{guild_name}'.",
                        url=f"https://discord.com/users/{m_id}",
                        bot_invite_url=bot_invite
                    )

    # 7. Fallback: Bot in server, but creator account not confirmed
    return DiscordProfile(
        discord_invite=invite_url,
        guild_id=guild_id,
        guild_name=guild_name,
        guild_icon=guild_icon,
        approximate_member_count=member_count,
        bot_in_guild=True,
        status="discovered",
        discovery_status="creator_not_identified",
        discovery_note=f"Arclent Bot is in '{guild_name}', but creator's user account could not be unambiguously identified among members. Please enter User ID manually.",
        url=invite_url,
        bot_invite_url=bot_invite
    )


async def recheck_bot_in_guild(
    guild_id: str,
    creator_name: str = "",
    channel_name: str = "",
    channel_handle: str = "",
    existing_invite: str = ""
) -> DiscordProfile:
    """Recheck whether the Arclent bot has been added to a Discord guild and resolve the creator."""
    clean_gid = (guild_id or "").strip()
    bot_invite = generate_bot_invite_url(clean_gid)
    invite_url = existing_invite or f"https://discord.com"

    if not clean_gid:
        return DiscordProfile(
            discord_invite=invite_url,
            status="discovered",
            discovery_status="invalid_guild",
            discovery_note="No valid server ID provided to check bot presence.",
            bot_invite_url=bot_invite
        )

    guild_details = await check_bot_in_guild(clean_gid)
    if not guild_details:
        return DiscordProfile(
            discord_invite=invite_url,
            guild_id=clean_gid,
            bot_in_guild=False,
            status="discovered",
            discovery_status="bot_not_in_server",
            discovery_note="Arclent Bot has not yet joined this server. Please click 'Add Bot to Server' to authorize it.",
            url=invite_url,
            bot_invite_url=bot_invite
        )

    guild_name = guild_details.get("name") or "Discord Server"
    guild_icon = guild_details.get("icon")
    member_count = guild_details.get("approximate_member_count")

    # Bot is present! Attempt identification
    owner_id = str(guild_details.get("owner_id")) if guild_details.get("owner_id") else None
    owner_member = await get_guild_member(clean_gid, owner_id) if owner_id else None
    owner_user = (owner_member.get("user") if owner_member else {}) or {}
    owner_username = owner_user.get("username") or (owner_member.get("nick") if owner_member else None)
    owner_global = owner_user.get("global_name") or ""

    c_candidates = [creator_name, channel_name, channel_handle]
    clean_names = [re.sub(r'[^a-z0-9]', '', c.lower()) for c in c_candidates if c]
    owner_text = re.sub(r'[^a-z0-9]', '', f"{owner_username or ''} {owner_global}".lower())
    clean_gname = re.sub(r'[^a-z0-9]', '', guild_name.lower())

    is_owner_match = False
    if clean_names and any(cn in owner_text or owner_text in cn for cn in clean_names if len(cn) >= 3):
        is_owner_match = True
    elif clean_names and any(cn in clean_gname for cn in clean_names if len(cn) >= 3):
        is_owner_match = True
    elif owner_username and not clean_names:
        is_owner_match = True

    if is_owner_match and owner_id and owner_username:
        return DiscordProfile(
            discord_invite=invite_url,
            discord_username=owner_username,
            discord_user_id=owner_id,
            guild_id=clean_gid,
            guild_name=guild_name,
            guild_icon=guild_icon,
            approximate_member_count=member_count,
            bot_in_guild=True,
            status="sendable",
            discovery_status="identified",
            discovery_note=f"Identified server owner @{owner_username} as creator in '{guild_name}'.",
            url=f"https://discord.com/users/{owner_id}",
            bot_invite_url=bot_invite
        )

    # Search members
    for c_cand in c_candidates:
        clean_cand = c_cand.replace("@", "").strip()
        if len(clean_cand) >= 3:
            search_results = await search_guild_members(clean_gid, clean_cand, limit=3)
            for m in search_results:
                m_user = m.get("user") or {}
                m_id = str(m_user.get("id")) if m_user.get("id") else None
                m_name = m_user.get("username") or m.get("nick")
                if m_id and m_name:
                    return DiscordProfile(
                        discord_invite=invite_url,
                        discord_username=m_name,
                        discord_user_id=m_id,
                        guild_id=clean_gid,
                        guild_name=guild_name,
                        guild_icon=guild_icon,
                        approximate_member_count=member_count,
                        bot_in_guild=True,
                        status="sendable",
                        discovery_status="identified",
                        discovery_note=f"Identified member @{m_name} matching '{c_cand}' in '{guild_name}'.",
                        url=f"https://discord.com/users/{m_id}",
                        bot_invite_url=bot_invite
                    )

    # Fallback if owner not identified
    return DiscordProfile(
        discord_invite=invite_url,
        guild_id=clean_gid,
        guild_name=guild_name,
        guild_icon=guild_icon,
        approximate_member_count=member_count,
        bot_in_guild=True,
        status="discovered",
        discovery_status="creator_not_identified",
        discovery_note=f"Arclent Bot confirmed in '{guild_name}'! Creator's account could not be automatically identified; please enter User ID manually.",
        url=invite_url,
        bot_invite_url=bot_invite
    )
