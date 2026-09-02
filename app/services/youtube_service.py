"""YouTube service for extracting video and creator metadata."""

import re
import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    if not url:
        return None

    url = url.strip()
    
    # Check youtu.be shortlinks
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)
            
    # Check shorts
    if "/shorts/" in url:
        match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)
            
    # Check embed
    if "/embed/" in url:
        match = re.search(r"/embed/([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)
            
    # Check standard /watch?v=
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            return query["v"][0]

    # Generic fallback 11-char regex for YouTube ID
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if match:
        return match.group(1)

    return None


async def fetch_via_youtube_api(video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch video and channel data using official Google YouTube Data API v3."""
    if not settings.YOUTUBE_API_KEY:
        return None

    try:
        from googleapiclient.discovery import build
        
        youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY, cache_discovery=False)
        
        # 1. Fetch Video Details
        video_response = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        ).execute()

        items = video_response.get("items", [])
        if not items:
            logger.warning(f"Video {video_id} not found via YouTube API")
            return None

        video_item = items[0]
        snippet = video_item.get("snippet", {})
        channel_id = snippet.get("channelId")
        video_title = snippet.get("title", "")
        description = snippet.get("description", "")
        published_at = snippet.get("publishedAt", "")
        thumbnails = snippet.get("thumbnails", {})
        video_thumbnail = (
            thumbnails.get("maxres", {}).get("url") or 
            thumbnails.get("high", {}).get("url") or 
            thumbnails.get("default", {}).get("url")
        )

        # 2. Fetch Channel Details
        channel_name = snippet.get("channelTitle", "")
        channel_handle = None
        subscriber_count = None
        profile_image = video_thumbnail
        channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else None

        if channel_id:
            channel_response = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=channel_id
            ).execute()
            
            c_items = channel_response.get("items", [])
            if c_items:
                c_item = c_items[0]
                c_snippet = c_item.get("snippet", {})
                c_stats = c_item.get("statistics", {})
                
                channel_name = c_snippet.get("title", channel_name)
                channel_handle = c_snippet.get("customUrl")
                if channel_handle and not channel_handle.startswith("@"):
                    channel_handle = f"@{channel_handle}"
                
                if channel_handle:
                    channel_url = f"https://www.youtube.com/{channel_handle}"
                    
                c_thumbs = c_snippet.get("thumbnails", {})
                profile_image = (
                    c_thumbs.get("high", {}).get("url") or 
                    c_thumbs.get("medium", {}).get("url") or 
                    profile_image
                )
                
                subs = c_stats.get("subscriberCount")
                if subs:
                    subs_int = int(subs)
                    if subs_int >= 1_000_000:
                        subscriber_count = f"{subs_int / 1_000_000:.1f}M subscribers"
                    elif subs_int >= 1_000:
                        subscriber_count = f"{subs_int / 1_000:.1f}K subscribers"
                    else:
                        subscriber_count = f"{subs_int} subscribers"

        return {
            "video_id": video_id,
            "video_title": video_title,
            "creator_name": channel_name,
            "channel_name": channel_name,
            "channel_handle": channel_handle or f"@{channel_name.lower().replace(' ', '')}",
            "channel_url": channel_url or f"https://www.youtube.com/watch?v=VIDEO_ID",
            "profile_image": profile_image,
            "subscriber_count": subscriber_count or "Subscribers count unavailable",
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "description": description,
            "published_at": published_at,
            "source": "official_youtube_api"
        }
    except Exception as e:
        logger.error(f"Error fetching from YouTube API: {e}", exc_info=True)
        return None


async def fetch_via_public_fallback(video_id: str) -> Dict[str, Any]:
    """Fallback YouTube extractor using YouTube oEmbed and public webpage scraping."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
        # 1. Fetch oEmbed metadata
        oembed_url = f"https://www.youtube.com/oembed?url={video_url}&format=json"
        oembed_data = {}
        try:
            resp = await client.get(oembed_url)
            if resp.status_code == 200:
                oembed_data = resp.json()
        except Exception as e:
            logger.warning(f"oEmbed fetch failed for {video_id}: {e}")

        # 2. Fetch watch page HTML to extract full description & metadata
        html_resp = await client.get(video_url)
        if html_resp.status_code != 200:
            raise ValueError(f"Could not retrieve YouTube video page. HTTP {html_resp.status_code}")

        soup = BeautifulSoup(html_resp.text, "html.parser")
        
        video_title = oembed_data.get("title")
        if not video_title:
            meta_title = soup.find("meta", property="og:title")
            video_title = meta_title["content"] if meta_title and meta_title.get("content") else f"YouTube Video ({video_id})"

        creator_name = oembed_data.get("author_name")
        channel_url = oembed_data.get("author_url")
        
        # Extract metadata from JSON-LD if present
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        description = ""
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if not creator_name and "author" in data:
                        creator_name = data["author"]
                    if not description and "description" in data:
                        description = data["description"]
            except Exception:
                continue

        # Extract meta description
        if not description:
            meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"]

        # Extract channel info from HTML
        profile_image = oembed_data.get("thumbnail_url")
        if not profile_image:
            meta_image = soup.find("meta", property="og:image")
            profile_image = meta_image["content"] if meta_image and meta_image.get("content") else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        # Try to parse ytInitialData for complete description and channel handle
        channel_handle = None
        subscriber_count = None
        
        try:
            initial_data_match = re.search(r"var ytInitialData = ({.*?});</script>", html_resp.text)
            if initial_data_match:
                yt_data = json.loads(initial_data_match.group(1))
                
                # Search for description and author
                def find_key(obj, key):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k == key:
                                yield v
                            if isinstance(v, (dict, list)):
                                yield from find_key(v, key)
                    elif isinstance(obj, list):
                        for item in obj:
                            yield from find_key(item, key)

                # Look for subscriber count text
                for sub_text in find_key(yt_data, "subscriberCountText"):
                    if isinstance(sub_text, dict) and "simpleText" in sub_text:
                        subscriber_count = sub_text["simpleText"]
                        break
                    elif isinstance(sub_text, dict) and "runs" in sub_text:
                        subscriber_count = "".join(r.get("text", "") for r in sub_text["runs"])
                        break

                # Look for channel owner name
                if not creator_name:
                    for owner in find_key(yt_data, "owner"):
                        if isinstance(owner, dict) and "videoOwnerRenderer" in owner:
                            title_obj = owner["videoOwnerRenderer"].get("title", {})
                            runs = title_obj.get("runs", [])
                            if runs:
                                creator_name = runs[0].get("text")
                                break
        except Exception as e:
            logger.debug(f"ytInitialData parsing note: {e}")

        channel_name = creator_name or "YouTube Creator"
        
        if channel_url and "@" in channel_url:
            channel_handle = "@" + channel_url.split("@")[-1].split("/")[0]
        else:
            channel_handle = f"@{channel_name.lower().replace(' ', '')}"

        return {
            "video_id": video_id,
            "video_title": video_title,
            "creator_name": channel_name,
            "channel_name": channel_name,
            "channel_handle": channel_handle,
            "channel_url": channel_url or f"https://www.youtube.com/{channel_handle}",
            "profile_image": profile_image,
            "subscriber_count": subscriber_count or "Active Creator",
            "video_url": video_url,
            "description": description or "No video description provided.",
            "published_at": None,
            "source": "public_fallback_extractor"
        }


async def get_youtube_metadata(video_url: str) -> Dict[str, Any]:
    """Main entrypoint for YouTube metadata extraction.
    
    Validates URL, extracts ID, tries YouTube Data API v3, and falls back gracefully.
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        raise ValueError(f"Could not extract a valid YouTube video ID from URL: {video_url}")

    # Try official API if key provided
    if settings.YOUTUBE_API_KEY:
        data = await fetch_via_youtube_api(video_id)
        if data:
            return data

    # Use public resilient fallback
    return await fetch_via_public_fallback(video_id)
