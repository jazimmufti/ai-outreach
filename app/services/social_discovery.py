"""Social media profile discovery and normalization.

Restricted strictly to supported platforms:
- Instagram
- X (Twitter)
- Discord
- Reddit
- Facebook
- LinkedIn
"""

import re
import logging
import urllib.parse
from typing import List, Set, Optional
from urllib.parse import urlparse

from app.models.schemas import SocialProfile

logger = logging.getLogger(__name__)

EXCLUDED_USERNAMES = {
    "intent", "share", "sharer", "home", "search", "explore", "login", 
    "signup", "hashtag", "privacy", "terms", "about", "help", "support",
    "pages", "watch", "live", "direct", "stories", "p", "reel", "reels",
    "status", "post", "posts", "i", "settings", "notifications", "r", "u", "user", "invite",
    "com", "net", "org", "null", "undefined", "true", "false", "link", "links",
    "channel", "video", "videos", "shorts", "feed", "youtube", "yt", "subscribe", "subscribers", "profile", "account", "accounts",
    "https", "http", "www", "follow", "like", "comment", "enquiries", "business", "contact",
    "instagram", "insta", "ig", "threads", "facebook", "fb", "twitter", "x", "tiktok", "discord", "linkedin", "snapchat",
    "credit", "credits", "editor", "edit", "vfx", "thumbnail", "contributor", "contributors"
}

KNOWN_SPONSORS_AND_BRANDS = {
    "anthropic", "openai", "claude", "chatgpt", "gemini", "google", "microsoft", "apple",
    "nordvpn", "expressvpn", "surfshark", "squarespace", "wix", "shopify",
    "betterhelp", "audible", "skillshare", "grammarly", "honey", "cashapp",
    "patreon", "subscribestar", "buymeacoffee", "kofi", "amazon", "merch"
}

# 1. Direct and redirect URL patterns
URL_PATTERNS = [
    {
        "platform": "Instagram",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})", re.I),
        "format_url": lambda u: f"https://instagram.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-").lstrip("@")
    },
    {
        "platform": "X",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]{1,20})", re.I),
        "format_url": lambda u: f"https://x.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-").lstrip("@")
    },
    {
        "platform": "Twitch",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?twitch\.tv\/([a-zA-Z0-9_]{3,25})", re.I),
        "format_url": lambda u: f"https://twitch.tv/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-").lstrip("@")
    },
    {
        "platform": "Discord",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg\/|discord\.com\/invite\/)([a-zA-Z0-9_-]{2,32})", re.I),
        "format_url": lambda u: f"https://discord.gg/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-")
    },
    {
        "platform": "Reddit",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?reddit\.com\/(?:r|user|u)\/([a-zA-Z0-9_\-]{2,32})", re.I),
        "format_url": lambda u: f"https://reddit.com/r/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-")
    },
    {
        "platform": "Facebook",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:facebook\.com|fb\.com)\/([a-zA-Z0-9_\.]{1,50})", re.I),
        "format_url": lambda u: f"https://facebook.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-")
    },
    {
        "platform": "LinkedIn",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/([a-zA-Z0-9_\-\.]{1,50})", re.I),
        "format_url": lambda u: f"https://linkedin.com/in/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].rstrip("./_…-")
    },
]

# 2. Text / Mention patterns (e.g. "Instagram: the.umar._", "Instagram - @the.umar._", "Twitter: @user")
TEXT_HANDLE_PATTERNS = [
    {
        "platform": "Instagram",
        "pattern": re.compile(r"\b(?:instagram|insta|ig)\b(?!\.com|\.am|\.org)\s*(?::|—|-|\||\/|\bat\b)?\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.]{2,30})\b", re.I),
        "format_url": lambda u: f"https://instagram.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "X",
        "pattern": re.compile(r"\b(?:twitter|x(?:\s*\(twitter\))?)\b(?!\.com|\.org|\.ai)\s*(?::|—|-|\||\/|\bat\b)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_]{2,20})\b", re.I),
        "format_url": lambda u: f"https://x.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "Twitch",
        "pattern": re.compile(r"\btwitch\b(?!\.tv|\.com)\s*(?::|—|-|\||\/|\bat\b)?\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_]{3,25})\b", re.I),
        "format_url": lambda u: f"https://twitch.tv/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "Discord",
        "pattern": re.compile(r"\bdiscord\b(?!\.com|\.gg)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_-]{2,32})\b", re.I),
        "format_url": lambda u: f"https://discord.gg/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "Reddit",
        "pattern": re.compile(r"\breddit\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)(?:u\/|r\/)?([a-zA-Z0-9_\-]{2,32})\b", re.I),
        "format_url": lambda u: f"https://reddit.com/r/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "Facebook",
        "pattern": re.compile(r"\b(?:facebook|fb)\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.]{2,50})\b", re.I),
        "format_url": lambda u: f"https://facebook.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
    {
        "platform": "LinkedIn",
        "pattern": re.compile(r"\blinkedin\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.-]{2,50})\b", re.I),
        "format_url": lambda u: f"https://linkedin.com/in/{u.rstrip('/')}",
        "clean_user": lambda u: u.rstrip("./_…-").lstrip("@").strip()
    },
]


def clean_social_text(text: str) -> str:
    """Unquote URL encodings and unwrap YouTube redirect links."""
    if not text:
        return ""
    
    # Pre-clean HTML entities like &amp; so parse_qs can properly parse parameters
    normalized = text.replace("&amp;", "&")
    unquoted = urllib.parse.unquote(normalized)
    
    def replace_redirect(match):
        full_url = match.group(0)
        try:
            parsed = urllib.parse.urlparse(full_url)
            q_val = urllib.parse.parse_qs(parsed.query).get("q", [])
            if q_val:
                return urllib.parse.unquote(q_val[0])
        except Exception:
            pass
        return full_url

    processed = re.sub(r"https?:\/\/(?:www\.)?youtube\.com\/redirect\?[^\s<>\"']+", replace_redirect, unquoted)
    return processed


def is_valid_username(user: str) -> bool:
    """Validate that extracted handle is a legitimate username and not metadata, sponsor, or truncated artifact."""
    if not user:
        return False
    user_clean = user.strip().lstrip("@").rstrip("./_…-")
    user_lower = user_clean.lower()

    # Reject truncated strings from YouTube text (e.g. siliconvall... or siliconvall… or text ending with dots)
    if ".." in user or "..." in user or "…" in user or user.endswith((".", "…")):
        return False
    if len(user_lower) < 2 or user_lower in EXCLUDED_USERNAMES:
        return False
    if any(user_lower.endswith(ext) for ext in [".com", ".net", ".org", ".am", ".ai", ".io", ".png", ".jpg", ".html", ".php"]):
        return False
    if user_lower.startswith(("http", "www.")):
        return False
    return True


def extract_social_profiles(text: str, source_label: str = "YouTube description") -> List[SocialProfile]:
    """Extract and normalize Instagram, X, Discord, Reddit, Facebook, and LinkedIn profiles from text."""
    if not text:
        return []

    cleaned_text = clean_social_text(text)
    discovered: List[SocialProfile] = []
    seen_urls = set()

    # 1. Extract direct and redirected URLs
    for item in URL_PATTERNS:
        for match in item["pattern"].finditer(cleaned_text):
            raw_user = match.group(1)
            # Check raw_user BEFORE cleaning to immediately reject truncated links ending in dots/ellipsis
            if ".." in raw_user or "..." in raw_user or "…" in raw_user or raw_user.endswith((".", "…", "-", "_")):
                continue

            cleaned_user = item["clean_user"](raw_user)
            
            if not is_valid_username(cleaned_user):
                continue

            full_url = item["format_url"](cleaned_user)
            key = (item["platform"], full_url.lower())
            if key in seen_urls:
                continue

            seen_urls.add(key)
            discovered.append(
                SocialProfile(
                    platform=item["platform"],
                    username=cleaned_user,
                    url=full_url,
                    source=source_label,
                    confidence="high"
                )
            )

    # 2. Extract text mentions / handle labels (e.g. "Instagram: the.umar._")
    for line in cleaned_text.splitlines():
        line = line.strip()
        if not line:
            continue
            
        for item in TEXT_HANDLE_PATTERNS:
            for match in item["pattern"].finditer(line):
                raw_user = match.group(1)
                # Check raw_user BEFORE cleaning
                if ".." in raw_user or "..." in raw_user or "…" in raw_user or raw_user.endswith((".", "…", "-", "_")):
                    continue

                cleaned_user = item["clean_user"](raw_user)
                
                if not is_valid_username(cleaned_user):
                    continue

                full_url = item["format_url"](cleaned_user)
                key = (item["platform"], full_url.lower())
                if key in seen_urls:
                    continue

                seen_urls.add(key)
                discovered.append(
                    SocialProfile(
                        platform=item["platform"],
                        username=cleaned_user,
                        url=full_url,
                        source=source_label,
                        confidence="high"
                    )
                )

    return discovered


def rank_social_profiles(
    profiles: List[SocialProfile],
    creator_name: str = "",
    channel_name: str = "",
    channel_handle: str = ""
) -> List[SocialProfile]:
    """Score and rank social profiles so the true creator handle is ranked first, discarding sponsors and truncated duplicates."""
    if not profiles:
        return []

    c_name = re.sub(r'[^a-zA-Z0-9]', '', (creator_name or '').lower())
    c_chan = re.sub(r'[^a-zA-Z0-9]', '', (channel_name or '').lower())
    c_hdl = re.sub(r'[^a-zA-Z0-9]', '', (channel_handle or '').lower()).lstrip('@')

    target_tokens = {t for t in [c_name, c_chan, c_hdl] if len(t) >= 3}

    # Remove truncated prefix duplicates on the same platform (e.g. 'siliconvall' when 'siliconvalleygirl' exists)
    cleaned_candidates: List[SocialProfile] = []
    platform_usernames = {}
    for p in profiles:
        u = re.sub(r'[^a-zA-Z0-9]', '', (p.username or '').lower())
        platform_usernames.setdefault(p.platform, []).append(u)

    for p in profiles:
        p_user = re.sub(r'[^a-zA-Z0-9]', '', (p.username or '').lower())
        
        # Check if this user is a strict prefix/substring of another longer username on the same platform
        is_truncated_duplicate = False
        for other_u in platform_usernames.get(p.platform, []):
            if len(other_u) > len(p_user) and other_u.startswith(p_user):
                is_truncated_duplicate = True
                break
        if is_truncated_duplicate:
            continue

        # Discard known sponsor/company names if not matching creator name
        if p_user in KNOWN_SPONSORS_AND_BRANDS and not any(t == p_user for t in target_tokens):
            continue

        cleaned_candidates.append(p)

    def score_profile(profile: SocialProfile) -> float:
        score = 0.0
        p_user = re.sub(r'[^a-zA-Z0-9]', '', (profile.username or '').lower())
        
        # Exact match with creator name, channel name, or handle
        if any(p_user == t for t in target_tokens):
            score += 200.0
        # Substring / partial match
        elif any(t in p_user or p_user in t for t in target_tokens if len(p_user) >= 3):
            score += 100.0
            
        # Source authority boost
        src = (profile.source or "").lower()
        if "links" in src:
            score += 50.0
        elif "channel description" in src:
            score += 30.0
        elif "video description" in src:
            score += 10.0

        # Platform priority (Instagram first for 2-step verification)
        if profile.platform == "Instagram":
            score += 15.0

        return score

    return sorted(cleaned_candidates, key=score_profile, reverse=True)


def extract_website_urls(text: str) -> List[str]:
    """Extract personal website URLs from text for email crawling only."""
    if not text:
        return []

    cleaned_text = clean_social_text(text)
    website_urls: List[str] = []
    seen = set()

    general_urls = re.findall(r"https?:\/\/[^\s<>\"'()]+", cleaned_text)
    for raw_url in general_urls:
        raw_url = raw_url.rstrip(".,;)>\"'")
        try:
            parsed = urlparse(raw_url)
            domain = parsed.netloc.lower()
            
            # Skip non-creator/social domains
            if any(skip in domain for skip in [
                "youtube.com", "youtu.be", "google.com", "instagram.com", "twitter.com", 
                "x.com", "linkedin.com", "tiktok.com", "facebook.com", "fb.com", "github.com",
                "apple.com", "spotify.com", "amazon.com", "amzn.to", "bit.ly", "patreon.com",
                "discord.gg", "discord.com", "reddit.com"
            ]):
                continue

            if domain and "." in domain and not domain.endswith((".png", ".jpg", ".jpeg", ".webp", ".mp4")):
                clean_site_url = f"{parsed.scheme}://{parsed.netloc}"
                if clean_site_url.lower() not in seen:
                    seen.add(clean_site_url.lower())
                    website_urls.append(clean_site_url)
        except Exception:
            continue

    return website_urls


async def discover_credits_social_profiles(
    text: str,
    source_label: str = "YouTube description",
    linked_platform: Optional[str] = None,
    linked_account: Optional[str] = None
) -> List[SocialProfile]:
    """Find contributor/credit mentions without specified platform (e.g. 'editor: @ummer.04'),
    verify which platforms they exist on (Instagram, X, Facebook, Twitch, Discord),
    and construct SocialProfile objects.
    
    If an account is linked on a specific platform (e.g. Instagram '@ummer.04' or X '@user'),
    and the description does not mention a platform, it assumes the linked platform.
    """
    if not text:
        return []

    from app.services.youtube_description_parser import extract_verified_contributor_accounts

    try:
        verified_contributors = await extract_verified_contributor_accounts(
            text,
            linked_platform=linked_platform,
            linked_account=linked_account
        )
    except Exception as e:
        logger.debug(f"Contributor account verification note: {e}")
        return []

    discovered: List[SocialProfile] = []
    seen = set()

    for item in verified_contributors:
        username = item["username"]
        role = item.get("role", "credit")
        platforms = item.get("platforms", [])
        urls = item.get("urls", {})

        for plat in platforms:
            url = urls.get(plat)
            if not url:
                continue
            key = (plat, url.lower())
            if key not in seen:
                seen.add(key)
                src = f"{source_label} ({role}: @{username})"
                discovered.append(
                    SocialProfile(
                        platform=plat,
                        username=username,
                        url=url,
                        source=src,
                        confidence="high"
                    )
                )

    return discovered

