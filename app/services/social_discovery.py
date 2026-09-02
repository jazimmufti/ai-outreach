"""Social media profile discovery and normalization.

Restricted strictly to:
- Instagram
- X (Twitter)
- Discord
- Reddit
- Facebook
"""

import re
import logging
from typing import List
from urllib.parse import urlparse

from app.models.schemas import SocialProfile

logger = logging.getLogger(__name__)

# Strictly permitted platforms
ALLOWED_SOCIAL_PATTERNS = [
    {
        "platform": "Instagram",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:instagram\.com|instagr\.am)\/([a-zA-Z0-9_\.]{1,30})",
        "format_url": lambda u: f"https://instagram.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].lstrip("@")
    },
    {
        "platform": "X",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]{1,20})",
        "format_url": lambda u: f"https://x.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0].lstrip("@")
    },
    {
        "platform": "Discord",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:discord\.gg\/|discord\.com\/invite\/)([a-zA-Z0-9_-]{2,32})",
        "format_url": lambda u: f"https://discord.gg/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "Reddit",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?reddit\.com\/(?:r|user|u)\/([a-zA-Z0-9_\-]{2,32})",
        "format_url": lambda u: f"https://reddit.com/r/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "Facebook",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?(?:facebook\.com|fb\.com)\/([a-zA-Z0-9_\.]{1,50})",
        "format_url": lambda u: f"https://facebook.com/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
    {
        "platform": "LinkedIn",
        "pattern": r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/([a-zA-Z0-9_\-\.]{1,50})",
        "format_url": lambda u: f"https://linkedin.com/in/{u.rstrip('/')}",
        "clean_user": lambda u: u.replace("/", "").replace("?", "").split("&")[0]
    },
]

EXCLUDED_USERNAMES = {
    "intent", "share", "sharer", "home", "search", "explore", "login", 
    "signup", "hashtag", "privacy", "terms", "about", "help", "support",
    "pages", "watch", "live", "direct", "stories", "p", "reel", "reels",
    "status", "post", "posts", "i", "settings", "notifications", "r", "u", "user", "invite"
}


def extract_social_profiles(text: str, source_label: str = "YouTube description") -> List[SocialProfile]:
    """Extract ONLY Instagram, X, Discord, Reddit, and Facebook profiles from text."""
    if not text:
        return []

    discovered: List[SocialProfile] = []
    seen_urls = set()

    for item in ALLOWED_SOCIAL_PATTERNS:
        matches = re.finditer(item["pattern"], text, re.IGNORECASE)
        for match in matches:
            raw_user = match.group(1)
            cleaned_user = item["clean_user"](raw_user)
            
            # Skip invalid paths or system routes
            if not cleaned_user or cleaned_user.lower() in EXCLUDED_USERNAMES:
                continue

            full_url = item["format_url"](cleaned_user)
            if full_url.lower() in seen_urls:
                continue

            seen_urls.add(full_url.lower())
            
            confidence = "high" if "social" in text.lower() or "follow" in text.lower() or "join" in text.lower() or "community" in text.lower() else "medium"
            
            discovered.append(
                SocialProfile(
                    platform=item["platform"],
                    username=cleaned_user,
                    url=full_url,
                    source=source_label,
                    confidence=confidence
                )
            )

    return discovered


def extract_website_urls(text: str) -> List[str]:
    """Extract personal website URLs from text for email crawling only."""
    if not text:
        return []

    website_urls: List[str] = []
    seen = set()

    general_urls = re.findall(r"https?:\/\/[^\s<>\"'()]+", text)
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
