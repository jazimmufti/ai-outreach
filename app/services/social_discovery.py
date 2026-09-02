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
from typing import List, Set
from urllib.parse import urlparse

from app.models.schemas import SocialProfile

logger = logging.getLogger(__name__)

EXCLUDED_USERNAMES = {
    "intent", "share", "sharer", "home", "search", "explore", "login", 
    "signup", "hashtag", "privacy", "terms", "about", "help", "support",
    "pages", "watch", "live", "direct", "stories", "p", "reel", "reels",
    "status", "post", "posts", "i", "settings", "notifications", "r", "u", "user", "invite",
    "com", "net", "org", "null", "undefined", "true", "false", "link", "links",
    "channel", "video", "youtube", "subscribe", "subscribers", "profile", "account",
    "https", "http", "www", "follow", "like", "comment", "enquiries", "business", "contact"
}

# 1. Direct and redirect URL patterns
URL_PATTERNS = [
    {
        "platform": "Instagram",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})", re.I),
        "format_url": lambda u: f"https://instagram.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].lstrip("@")
    },
    {
        "platform": "X",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]{1,20})", re.I),
        "format_url": lambda u: f"https://x.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].lstrip("@")
    },
    {
        "platform": "Discord",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg\/|discord\.com\/invite\/)([a-zA-Z0-9_-]{2,32})", re.I),
        "format_url": lambda u: f"https://discord.gg/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "Reddit",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?reddit\.com\/(?:r|user|u)\/([a-zA-Z0-9_\-]{2,32})", re.I),
        "format_url": lambda u: f"https://reddit.com/r/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "Facebook",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:facebook\.com|fb\.com)\/([a-zA-Z0-9_\.]{1,50})", re.I),
        "format_url": lambda u: f"https://facebook.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "LinkedIn",
        "pattern": re.compile(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/([a-zA-Z0-9_\-\.]{1,50})", re.I),
        "format_url": lambda u: f"https://linkedin.com/in/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
]

# 2. Text / Mention patterns (e.g. "Instagram: the.umar._", "Instagram - @the.umar._", "Twitter: @user")
TEXT_HANDLE_PATTERNS = [
    {
        "platform": "Instagram",
        "pattern": re.compile(r"\b(?:instagram|insta|ig)\b(?!\.com|\.am|\.org)\s*(?::|—|-|\||\/|\bat\b)?\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.]{2,30})\b", re.I),
        "format_url": lambda u: f"https://instagram.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
    {
        "platform": "X",
        "pattern": re.compile(r"\b(?:twitter|x(?:\s*\(twitter\))?)\b(?!\.com|\.org|\.ai)\s*(?::|—|-|\||\/|\bat\b)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_]{2,20})\b", re.I),
        "format_url": lambda u: f"https://x.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
    {
        "platform": "Discord",
        "pattern": re.compile(r"\bdiscord\b(?!\.com|\.gg)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_-]{2,32})\b", re.I),
        "format_url": lambda u: f"https://discord.gg/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
    {
        "platform": "Reddit",
        "pattern": re.compile(r"\breddit\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)(?:u\/|r\/)?([a-zA-Z0-9_\-]{2,32})\b", re.I),
        "format_url": lambda u: f"https://reddit.com/r/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
    {
        "platform": "Facebook",
        "pattern": re.compile(r"\b(?:facebook|fb)\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.]{2,50})\b", re.I),
        "format_url": lambda u: f"https://facebook.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
    {
        "platform": "LinkedIn",
        "pattern": re.compile(r"\blinkedin\b(?!\.com)\s*(?::|—|-|\||\/)\s*(?!https?:\/\/|www\.)@?([a-zA-Z0-9_.-]{2,50})\b", re.I),
        "format_url": lambda u: f"https://linkedin.com/in/{u.rstrip('/')}",
        "clean_user": lambda u: u.lstrip("@").strip()
    },
]


def clean_social_text(text: str) -> str:
    """Unquote URL encodings and unwrap YouTube redirect links."""
    if not text:
        return ""
    
    unquoted = urllib.parse.unquote(text)
    
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
    """Validate that extracted handle is a legitimate username and not metadata or domain artifact."""
    if not user:
        return False
    user_lower = user.lower().strip()
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
