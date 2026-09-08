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
from typing import List, Optional, Set

# System keywords and URL paths that should not be treated as user handles
EXCLUDED_INSTAGRAM_PATHS: Set[str] = {
    "p", "reel", "reels", "stories", "tv", "explore", "direct", "accounts",
    "login", "signup", "about", "help", "terms", "privacy", "press",
    "api", "developer", "jobs", "directory", "settings", "emails",
    "com", "org", "net", "null", "undefined", "true", "false", "profile",
    "channel", "video", "youtube", "subscribe", "subscribers", "contact",
    "business", "enquiries", "link", "links", "linktree", "bio", "www", "http", "https"
}

# Regex to detect Instagram URLs
INSTAGRAM_URL_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})",
    re.IGNORECASE
)

# Regex to detect explicitly prefixed Instagram handles (e.g. "Instagram: @user", "IG - user")
PREFIXED_HANDLE_REGEX = re.compile(
    r"\b(?:instagram|insta|ig|contributor|contributors|credit|credits|edited by|editor|vfx|thumbnail|collab|collaboration)\b"
    r"[\s\:\-\—\|]*"
    r"(?:@|https?:\/\/(?:www\.)?instagram\.com\/)?([a-zA-Z0-9_\.]{2,30})\b",
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

    # Check against system paths
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

    # Strategy 2: Extract from prefixed mentions (e.g. "Instagram: ummer.04" or "Contributor: @user")
    for match in PREFIXED_HANDLE_REGEX.finditer(processed_text):
        add_candidate(match.group(1))

    # Strategy 3: Extract from standard @mentions (e.g. "@ummer.04")
    for match in AT_MENTION_REGEX.finditer(processed_text):
        add_candidate(match.group(1))

    return discovered_usernames
