"""YouTube Description Parser.

Extracts and normalizes Instagram usernames and URLs mentioned in YouTube video descriptions.
Handles edge cases such as:
- Direct handles (@username)
- Prefixed handles (Instagram: @username, Contributor - @username, IG: username)
- Full URLs (https://instagram.com/username, https://www.instagram.com/username/)
- Obfuscated and redirect links (e.g. YouTube redirects)
- Punctuation, brackets, quotes, trailing dots, trailing slashes, and query parameters
- Case differences (normalizes to lowercase)
- Deduplication and system path filtering
"""

import re
import urllib.parse
from typing import List, Optional, Set, Dict, Any

# System keywords, platform names, and URL paths that should not be treated as user handles
EXCLUDED_INSTAGRAM_PATHS: Set[str] = {
    "p", "reel", "reels", "stories", "tv", "explore", "direct", "accounts", "account",
    "login", "signup", "about", "help", "terms", "privacy", "press",
    "api", "developer", "jobs", "directory", "settings", "emails",
    "com", "org", "net", "null", "undefined", "true", "false", "profile",
    "channel", "video", "videos", "shorts", "feed", "share", "like", "comment",
    "youtube", "yt", "subscribe", "subscribers", "contact", "everyone", "thanks",
    "business", "enquiries", "link", "links", "linktree", "bio", "www", "http", "https",
    "instagram", "insta", "ig", "threads", "facebook", "fb", "twitter", "x",
    "tiktok", "discord", "linkedin", "snapchat", "instagram.com", "www.instagram.com",
    "credit", "credits", "editor", "edit", "vfx", "thumbnail", "contributor", "contributors"
}

# Regex to detect Instagram URLs (with or without protocol/www)
INSTAGRAM_URL_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})",
    re.IGNORECASE
)

# Regex to detect explicitly prefixed Instagram handles
# (e.g. "Instagram: ummer.04", "IG: @ummer.04", "Insta - user")
INSTA_PREFIXED_HANDLE_REGEX = re.compile(
    r"\b(?:instagram|insta|ig)\b(?!\.com|\.org|\.net|\.am|\.ai|\.io)"
    r"[\s\:\-\—\|\–\>\•\*\~]*[^\w\s@\/]*[\s\:\-\—\|\–\>\•\*\~]*"
    r"(?:@|(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/)?"
    r"(?!https?:\/\/)([a-zA-Z0-9_\.]{2,30})\b",
    re.IGNORECASE
)

# Regex to detect general contributor / credit mentions
# (e.g. "Credits: @ummer.04", "Editor: @user", "Editor: https://instagram.com/user", "Editor: ummer.04")
# MUST have '@', or an Instagram URL, or contain handle-defining punctuation (. or _)
CREDIT_PREFIXED_HANDLE_REGEX = re.compile(
    r"\b(?:contributor|contributors|collaborator|collaborators|collab|collaboration|credit|credits|credited|edited by|editor|video editor|video edit|edit by|edit|vfx by|vfx|thumbnail by|thumbnail)\b"
    r"[\s\:\-\—\|\–\>\•\*\~]*[^\w\s@\/]*[\s\:\-\—\|\–\>\•\*\~]*"
    r"(?:"
        r"@([a-zA-Z0-9_\.]{2,30})"
        r"|"
        r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})"
        r"|"
        r"(?!https?:\/\/)([a-zA-Z0-9]*[_\.][a-zA-Z0-9_\.]{1,29})"
    r")\b",
    re.IGNORECASE
)

# Regex to detect standard @mentions in descriptions (e.g. "@ummer.04")
AT_MENTION_REGEX = re.compile(
    r"(?<![a-zA-Z0-9_\.])@([a-zA-Z0-9_\.]{2,30})(?![a-zA-Z0-9_\.])"
)


def clean_and_normalize_username(raw_handle: str) -> Optional[str]:
    """Clean and normalize a raw candidate handle.
    
    Strips leading '@', query params, hash fragments, trailing punctuation,
    and converts to lowercase.
    """
    if not raw_handle:
        return None

    handle = raw_handle.strip()

    # If it's a URL or contains query parameters
    if "?" in handle:
        handle = handle.split("?")[0]
    if "#" in handle:
        handle = handle.split("#")[0]

    # Remove leading '@' and slashes
    handle = handle.lstrip("@").strip().rstrip("/").strip()

    # Remove common trailing punctuation (e.g. dots, commas, exclamation marks, brackets, colons)
    handle = re.sub(r"[\.,!?:;\)\]\}\'\"]+$", "", handle)
    # Remove leading brackets or quotes if any slipped in
    handle = re.sub(r"^[\(\[\{\'\"]+", "", handle)

    # Normalize to lowercase
    handle = handle.lower().strip()

    # Instagram usernames: 1-30 characters, letters, numbers, periods, and underscores
    # Cannot start with a period or end with a period
    if not handle or len(handle) > 30:
        return None

    # Strip any ending or leading dots
    handle = handle.strip(".")

    if not re.match(r"^[a-zA-Z0-9_\.]+$", handle):
        return None

    # Must contain at least one alphanumeric character
    if not re.search(r"[a-zA-Z0-9]", handle):
        return None

    # Reject URLs, domain names, or file extensions that slipped through
    if handle.startswith(("http", "www.")) or any(handle.endswith(ext) for ext in [".com", ".net", ".org", ".co", ".io", ".ai", ".html", ".php"]):
        return None

    # Check against system paths and platform names
    if handle in EXCLUDED_INSTAGRAM_PATHS:
        return None

    return handle


def extract_instagram_accounts(description: Optional[str]) -> List[str]:
    """Extract and normalize all Instagram usernames mentioned in a YouTube description.
    
    Args:
        description: Raw text of the YouTube video description.
        
    Returns:
        List of unique, normalized, lowercase Instagram usernames in order of appearance.
    """
    if not description or not description.strip():
        return []

    # 1. Unquote URL encodings and unwrap any YouTube redirect links
    raw_text = urllib.parse.unquote(description)
    def replace_redirect(match):
        full_url = match.group(0)
        try:
            parsed = urllib.parse.urlparse(full_url)
            q_vals = urllib.parse.parse_qs(parsed.query).get("q", [])
            if q_vals:
                return urllib.parse.unquote(q_vals[0])
        except Exception:
            pass
        return full_url

    processed_text = re.sub(
        r"https?:\/\/(?:www\.)?youtube\.com\/redirect\?[^\s<>\"']+",
        replace_redirect,
        raw_text
    )

    discovered_usernames: List[str] = []
    seen: Set[str] = set()

    def add_candidate(cand: Optional[str]) -> None:
        normalized = clean_and_normalize_username(cand or "")
        if normalized and normalized not in seen:
            seen.add(normalized)
            discovered_usernames.append(normalized)

    # Strategy 1: Extract from full Instagram URLs
    for match in INSTAGRAM_URL_REGEX.finditer(processed_text):
        add_candidate(match.group(1))

    # Strategy 2: Extract from explicit Instagram prefixes (e.g. "Instagram: ummer.04", "IG: @user")
    for match in INSTA_PREFIXED_HANDLE_REGEX.finditer(processed_text):
        add_candidate(match.group(1))

    # Strategy 3: Extract from general contributor/credits prefixes with handle evidence
    for match in CREDIT_PREFIXED_HANDLE_REGEX.finditer(processed_text):
        for grp in match.groups():
            if grp:
                add_candidate(grp)

    # Strategy 4: Extract from standard @mentions (e.g. "@ummer.04")
    for match in AT_MENTION_REGEX.finditer(processed_text):
        add_candidate(match.group(1))

    return discovered_usernames


CREDIT_ROLE_PATTERN = re.compile(
    r"\b(contributor|contributors|collaborator|collaborators|collab|collaboration|credit|credits|credited|edited by|editor|video editor|video edit|edit by|edit|vfx by|vfx|thumbnail by|thumbnail)\b"
    r"[\s\:\-\—\|\–\>\•\*\~]*[^\w\s@\/]*[\s\:\-\—\|\–\>\•\*\~]*"
    r"(?:"
        r"@([a-zA-Z0-9_\.]{2,30})"
        r"|"
        r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am|x\.com|twitter\.com|facebook\.com|twitch\.tv)\/([a-zA-Z0-9_\.]{1,30})"
        r"|"
        r"(?!https?:\/\/)([a-zA-Z0-9]*[_\.][a-zA-Z0-9_\.]{1,29})"
    r")\b",
    re.IGNORECASE
)


def detect_specified_platform(text_snippet: str) -> Optional[str]:
    """Detect if a specific social platform name or URL domain is explicitly mentioned in the snippet."""
    if not text_snippet:
        return None
    lower = text_snippet.lower()
    if "instagram.com" in lower or "instagr.am" in lower or re.search(r"\b(instagram|insta|ig)\b", lower):
        return "Instagram"
    if "x.com" in lower or "twitter.com" in lower or re.search(r"\b(twitter)\b", lower) or re.search(r"(?:^|\s)x\s*[:\-\—]", lower):
        return "X"
    if "twitch.tv" in lower or re.search(r"\b(twitch)\b", lower):
        return "Twitch"
    if "facebook.com" in lower or re.search(r"\b(facebook|fb)\b", lower):
        return "Facebook"
    if "discord.gg" in lower or "discord.com" in lower or re.search(r"\b(discord)\b", lower):
        return "Discord"
    return None


def extract_credit_candidates(description: Optional[str]) -> List[Dict[str, Any]]:
    """Extract candidate usernames and their associated role/credit labels from a description.
    
    Returns:
        List of dicts: [{"username": "ummer.04", "role": "editor", "specified_platform": None}, ...]
    """
    if not description or not description.strip():
        return []

    raw_text = urllib.parse.unquote(description)
    results: List[Dict[str, Any]] = []
    seen_users: Set[str] = set()

    for match in CREDIT_ROLE_PATTERN.finditer(raw_text):
        role_label = (match.group(1) or "credit").lower()
        # The username is in groups 2, 3, or 4
        handle = None
        for g in match.groups()[1:]:
            if g:
                handle = clean_and_normalize_username(g)
                if handle:
                    break

        if handle and handle not in seen_users:
            seen_users.add(handle)
            # Find the line context to detect if a specific platform was explicitly mentioned
            start_idx = max(0, raw_text.rfind("\n", 0, match.start()))
            end_idx = raw_text.find("\n", match.end())
            if end_idx == -1:
                end_idx = len(raw_text)
            line_context = raw_text[start_idx:end_idx]
            specified_platform = detect_specified_platform(line_context)

            results.append({
                "username": handle,
                "role": role_label,
                "specified_platform": specified_platform
            })

    # Also capture any standalone @mentions that haven't been captured yet
    for match in AT_MENTION_REGEX.finditer(raw_text):
        handle = clean_and_normalize_username(match.group(1))
        if handle and handle not in seen_users:
            seen_users.add(handle)
            start_idx = max(0, raw_text.rfind("\n", 0, match.start()))
            end_idx = raw_text.find("\n", match.end())
            if end_idx == -1:
                end_idx = len(raw_text)
            line_context = raw_text[start_idx:end_idx]
            specified_platform = detect_specified_platform(line_context)

            results.append({
                "username": handle,
                "role": "mention",
                "specified_platform": specified_platform
            })

    return results


async def extract_verified_contributor_accounts(
    description: Optional[str],
    linked_platform: Optional[str] = None,
    linked_account: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Extract credit candidate usernames and verify which platforms they exist on.
    
    If an account is linked (e.g. Instagram '@ummer.04' or X '@user') and the description
    does not mention which platform, it assumes that linked platform and checks it exclusively.
    If no platform is linked, it checks across all supported platforms.
    
    Returns:
        List of dicts: [
            {
                "username": "ummer.04",
                "role": "editor",
                "platforms": ["Instagram"],
                "urls": {"Instagram": "https://instagram.com/ummer.04"}
            }, ...
        ]
    """
    candidates = extract_credit_candidates(description)
    if not candidates:
        return []

    from app.services.platform_verifier import verify_username_on_platforms
    from app.services.linked_account import (
        get_linked_platform,
        get_linked_instagram_account,
        normalize_instagram_username
    )
    import httpx

    # Determine effective linked platform
    if linked_account is not None:
        norm_acc = normalize_instagram_username(linked_account)
        eff_platform = (linked_platform or "Instagram") if norm_acc else None
    else:
        active_acc = get_linked_instagram_account()
        eff_platform = linked_platform or (get_linked_platform() if active_acc else None)

    verified_list: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=6.0) as client:
        for cand in candidates:
            username = cand["username"]
            role = cand["role"]
            specified = cand.get("specified_platform")

            # Determine platforms to verify for this candidate
            if specified:
                target_platforms = [specified]
            elif eff_platform:
                # User's platform is linked and description did not specify a platform:
                # Assume the linked platform and verify on that platform ONLY.
                target_platforms = [eff_platform]
            else:
                # Unlinked: check across all supported platforms
                target_platforms = ["Instagram", "X", "Facebook", "Twitch", "Discord"]

            plat_results = await verify_username_on_platforms(
                username, client=client, platforms=target_platforms
            )

            existing_platforms = [p for p, exists in plat_results.items() if exists]
            urls = {}
            for p in existing_platforms:
                if p == "Instagram":
                    urls[p] = f"https://instagram.com/{username}"
                elif p == "X":
                    urls[p] = f"https://x.com/{username}"
                elif p == "Facebook":
                    urls[p] = f"https://facebook.com/{username}"
                elif p == "Twitch":
                    urls[p] = f"https://twitch.tv/{username}"
                elif p == "Discord":
                    urls[p] = f"https://discord.gg/{username}"

            verified_list.append({
                "username": username,
                "role": role,
                "platforms": existing_platforms,
                "urls": urls
            })

    return verified_list

