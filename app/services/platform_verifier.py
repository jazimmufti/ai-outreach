"""Platform existence verifier for social handles.

Checks whether a username exists on:
- Instagram
- X (Twitter)
- Facebook
- Twitch
- Discord
"""

import re
import asyncio
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

HEADERS_DESKTOP = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS_MOBILE = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    "Accept-Language": "en-US,en;q=0.9",
}

HEADERS_FB = {
    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Accept-Language": "en-US,en;q=0.9",
}


async def check_instagram_exists(username: str, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if an Instagram username exists by inspecting profile response with mobile UA."""
    clean_user = username.strip().lstrip("@")
    if not clean_user or len(clean_user) > 30:
        return False

    url = f"https://www.instagram.com/{clean_user}/"
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        should_close = True

    try:
        r = await client.get(url, headers=HEADERS_MOBILE, follow_redirects=True)
        if r.status_code != 200:
            return False
        has_og = 'property="og:title"' in r.text or 'property="og:description"' in r.text
        has_not_found = "Page Not Found" in r.text or "isn't available" in r.text or "page could not be found" in r.text.lower()
        return has_og and not has_not_found
    except Exception as e:
        logger.debug(f"Instagram check error for {clean_user}: {e}")
        return False
    finally:
        if should_close:
            await client.aclose()


async def check_x_exists(username: str, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if an X (Twitter) handle exists by inspecting profile page title."""
    clean_user = username.strip().lstrip("@")
    if not clean_user or len(clean_user) > 20:
        return False

    url = f"https://x.com/{clean_user}"
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        should_close = True

    try:
        r = await client.get(url, headers=HEADERS_DESKTOP, follow_redirects=True)
        if r.status_code != 200:
            return False
        m = re.search(r"<title>(.*?)</title>", r.text)
        title = m.group(1).strip() if m else ""
        return f"@{clean_user.lower()}" in title.lower()
    except Exception as e:
        logger.debug(f"X check error for {clean_user}: {e}")
        return False
    finally:
        if should_close:
            await client.aclose()


async def check_facebook_exists(username: str, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if a Facebook profile or page exists using crawler UA."""
    clean_user = username.strip().lstrip("@")
    if not clean_user or len(clean_user) > 50:
        return False

    url = f"https://www.facebook.com/{clean_user}"
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        should_close = True

    try:
        r = await client.get(url, headers=HEADERS_FB, follow_redirects=True)
        if r.status_code != 200:
            return False
        m = re.search(r"<title>(.*?)</title>", r.text)
        title = m.group(1).strip() if m else ""
        return bool(title) and title.lower() not in {"facebook", "log into facebook", "error"}
    except Exception as e:
        logger.debug(f"Facebook check error for {clean_user}: {e}")
        return False
    finally:
        if should_close:
            await client.aclose()


async def check_twitch_exists(username: str, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if a Twitch channel exists by checking channel title."""
    clean_user = username.strip().lstrip("@")
    if not clean_user or len(clean_user) > 25:
        return False

    url = f"https://www.twitch.tv/{clean_user}"
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        should_close = True

    try:
        r = await client.get(url, headers=HEADERS_DESKTOP, follow_redirects=True)
        if r.status_code != 200:
            return False
        m = re.search(r"<title>(.*?)</title>", r.text)
        title = m.group(1).strip() if m else ""
        return title.lower() != "twitch" and "twitch" in title.lower()
    except Exception as e:
        logger.debug(f"Twitch check error for {clean_user}: {e}")
        return False
    finally:
        if should_close:
            await client.aclose()


async def check_discord_exists(username: str, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Check if a Discord server vanity invite exists for username."""
    clean_user = username.strip().lstrip("@")
    if not clean_user:
        return False

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=4.0)
        should_close = True

    try:
        # Check vanity or invite code
        r = await client.get(f"https://discord.com/api/v9/invites/{clean_user}")
        return r.status_code == 200
    except Exception as e:
        logger.debug(f"Discord check error for {clean_user}: {e}")
        return False
    finally:
        if should_close:
            await client.aclose()


async def verify_username_on_platforms(
    username: str,
    client: Optional[httpx.AsyncClient] = None,
    platforms: Optional[List[str]] = None
) -> Dict[str, bool]:
    """Check existence of a username across specified platforms or all supported platforms.
    
    Supported platforms: 'Instagram', 'X', 'Facebook', 'Twitch', 'Discord'.
    
    Args:
        username: Username handle to check.
        client: Optional shared httpx.AsyncClient.
        platforms: Optional list of platforms to test. If omitted, tests all 5 platforms.
        
    Returns:
        Dict mapping platform name ('Instagram', 'X', 'Facebook', 'Twitch', 'Discord') to bool.
    """
    clean_user = username.strip().lstrip("@")
    all_plats = ["Instagram", "X", "Facebook", "Twitch", "Discord"]
    result_dict = {p: False for p in all_plats}

    if not clean_user:
        return result_dict

    # Normalize requested platforms filter
    if platforms is not None:
        target_set = set()
        for p in platforms:
            p_clean = p.strip().capitalize()
            if p_clean in ("Twitter", "X"):
                target_set.add("X")
            elif p_clean in ("Instagram", "Facebook", "Twitch", "Discord"):
                target_set.add(p_clean)
    else:
        target_set = set(all_plats)

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=6.0)
        should_close = True

    try:
        tasks = []
        task_names = []

        if "Instagram" in target_set:
            tasks.append(check_instagram_exists(clean_user, client))
            task_names.append("Instagram")
        if "X" in target_set:
            tasks.append(check_x_exists(clean_user, client))
            task_names.append("X")
        if "Facebook" in target_set:
            tasks.append(check_facebook_exists(clean_user, client))
            task_names.append("Facebook")
        if "Twitch" in target_set:
            tasks.append(check_twitch_exists(clean_user, client))
            task_names.append("Twitch")
        if "Discord" in target_set:
            tasks.append(check_discord_exists(clean_user, client))
            task_names.append("Discord")

        if tasks:
            gather_res = await asyncio.gather(*tasks, return_exceptions=True)
            for name, val in zip(task_names, gather_res):
                result_dict[name] = bool(val) and not isinstance(val, Exception)

        return result_dict
    finally:
        if should_close:
            await client.aclose()


async def verify_usernames_across_platforms(
    usernames: List[str]
) -> Dict[str, Dict[str, bool]]:
    """Verify multiple usernames across platforms concurrently."""
    if not usernames:
        return {}

    async with httpx.AsyncClient(timeout=7.0) as client:
        tasks = [verify_username_on_platforms(u, client) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for u, res in zip(usernames, results):
            if isinstance(res, dict):
                output[u] = res
            else:
                output[u] = {
                    "Instagram": False, "X": False, "Facebook": False, "Twitch": False, "Discord": False
                }
        return output
