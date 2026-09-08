"""YouTube service for extracting video and creator metadata."""

import re
import json
import logging
import urllib.parse
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs
import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)


def parse_youtube_target(url: str) -> Dict[str, Any]:
    """Parse a YouTube URL or handle into a structured target dict.
    
    Supports:
    - Video URLs: watch?v=..., youtu.be/..., /shorts/..., /embed/..., m.youtube.com/...
    - Channel URLs: /@handle, /@handle/about, /channel/CHANNEL_ID, /c/CUSTOM, /user/USER
    - Direct handles: @handle or handle
    """
    if not url:
        return {"type": "unknown", "raw": ""}

    url = url.strip()

    # Direct handle string (e.g. @the.umar. or @channel)
    if url.startswith("@"):
        clean_handle = url.lstrip("@").split("/")[0].split("?")[0]
        return {
            "type": "channel",
            "handle": f"@{clean_handle}",
            "channel_url": f"https://www.youtube.com/@{clean_handle}",
            "raw": url
        }

    # Check youtu.be shortlinks
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        if match:
            return {"type": "video", "video_id": match.group(1), "raw": url}

    # Check shorts
    if "/shorts/" in url:
        match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", url)
        if match:
            return {"type": "video", "video_id": match.group(1), "raw": url}

    # Check embed
    if "/embed/" in url:
        match = re.search(r"/embed/([a-zA-Z0-9_-]{11})", url)
        if match:
            return {"type": "video", "video_id": match.group(1), "raw": url}

    # Check standard /watch?v=
    parsed = urlparse(url if "://" in url else f"https://{url}")
    path = parsed.path
    query = parse_qs(parsed.query)

    if "v" in query and query["v"]:
        return {"type": "video", "video_id": query["v"][0], "raw": url}

    # Channel handle URL: /@handle or /@handle/about
    if "/@" in path:
        match = re.search(r"/(@[a-zA-Z0-9_.-]+)", path)
        if match:
            handle = match.group(1)
            return {
                "type": "channel",
                "handle": handle,
                "channel_url": f"https://www.youtube.com/{handle}",
                "raw": url
            }

    # Channel ID URL: /channel/UC...
    if "/channel/" in path:
        match = re.search(r"/channel/([a-zA-Z0-9_-]+)", path)
        if match:
            cid = match.group(1)
            return {
                "type": "channel",
                "channel_id": cid,
                "channel_url": f"https://www.youtube.com/channel/{cid}",
                "raw": url
            }

    # Custom URL: /c/... or /user/...
    if "/c/" in path or "/user/" in path:
        match = re.search(r"/(c|user)/([a-zA-Z0-9_-]+)", path)
        if match:
            slug = match.group(2)
            return {
                "type": "channel",
                "custom_name": slug,
                "channel_url": f"https://www.youtube.com/{match.group(1)}/{slug}",
                "raw": url
            }

    # Generic fallback 11-char regex for YouTube ID
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match and ("watch" in url or "youtu.be" in url or len(url) <= 15):
        return {"type": "video", "video_id": match.group(1), "raw": url}

    # If it looks like a username or handle without @ (e.g. the.umar.)
    if "/" not in url and not url.startswith("http"):
        return {
            "type": "channel",
            "handle": f"@{url}",
            "channel_url": f"https://www.youtube.com/@{url}",
            "raw": url
        }

    return {"type": "unknown", "raw": url}


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL if present."""
    target = parse_youtube_target(url)
    if target.get("type") == "video":
        return target.get("video_id")
    return None


def format_subscribers(subs_int: int) -> str:
    """Format subscriber count to readable string."""
    if subs_int >= 1_000_000:
        return f"{subs_int / 1_000_000:.1f}M subscribers"
    elif subs_int >= 1_000:
        return f"{subs_int / 1_000:.1f}K subscribers"
    return f"{subs_int} subscribers"


async def scrape_channel_links_and_about(
    channel_handle: Optional[str] = None,
    channel_id: Optional[str] = None,
    channel_url: Optional[str] = None
) -> Dict[str, Any]:
    """Scrape channel page HTML to extract public external Links (Instagram, X, etc.) and about metadata."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    target_urls = []
    if channel_url and "youtube.com" in channel_url:
        target_urls.append(channel_url)
    if channel_handle:
        h = channel_handle if channel_handle.startswith("@") else f"@{channel_handle}"
        target_urls.append(f"https://www.youtube.com/{h}")
    if channel_id:
        target_urls.append(f"https://www.youtube.com/channel/{channel_id}")

    discovered_links: List[str] = []
    discovered_description = ""
    discovered_avatar = None
    seen_links = set()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
        for t_url in target_urls:
            try:
                resp = await client.get(t_url)
                if resp.status_code != 200:
                    continue

                # 1. Parse ytInitialData if present
                m = re.search(r"(?:var\s+|window\[\")?ytInitialData(?:\"\])?\s*=\s*({.*?});(?:<\/script>|var|window)", resp.text)
                if not m:
                    m = re.search(r"var ytInitialData = ({.*?});</script>", resp.text)

                if m:
                    try:
                        data = json.loads(m.group(1))

                        # Extract metadata description & avatar
                        meta = data.get("metadata", {}).get("channelMetadataRenderer", {})
                        if meta:
                            desc = meta.get("description", "")
                            if desc and not discovered_description:
                                discovered_description = desc
                            avatars = meta.get("avatar", {}).get("thumbnails", [])
                            if avatars and not discovered_avatar:
                                discovered_avatar = avatars[-1].get("url")

                        def collect_strings(obj):
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    yield from collect_strings(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    yield from collect_strings(item)
                            elif isinstance(obj, str):
                                yield obj

                        for s in collect_strings(data):
                            if "youtube.com/redirect" in s or "q=" in s:
                                try:
                                    clean_s = s.replace("&amp;", "&")
                                    parsed = urllib.parse.urlparse(clean_s)
                                    q_vals = urllib.parse.parse_qs(parsed.query).get("q", [])
                                    for q_val in q_vals:
                                        target_link = urllib.parse.unquote(q_val).strip()
                                        if target_link.startswith("http") and target_link.lower() not in seen_links:
                                            seen_links.add(target_link.lower())
                                            discovered_links.append(target_link)
                                except Exception:
                                    pass
                            elif s.startswith("http") and any(plat in s.lower() for plat in [
                                "instagram.com", "x.com", "twitter.com", "facebook.com", "fb.com", 
                                "discord.gg", "discord.com", "linkedin.com", "reddit.com", "tiktok.com", "twitch.tv"
                            ]):
                                target_link = s.strip()
                                if target_link.lower() not in seen_links:
                                    seen_links.add(target_link.lower())
                                    discovered_links.append(target_link)
                    except Exception as e:
                        logger.debug(f"ytInitialData parse note for {t_url}: {e}")

                # 2. Resilient fallback: extract redirect URLs and direct social URLs from raw HTML resp.text
                raw_redirects = re.findall(r"https?:\/\/(?:www\.)?youtube\.com\/redirect\?[^\s<>\"']+", resp.text)
                for r_url in raw_redirects:
                    clean_r_url = r_url.replace("&amp;", "&")
                    try:
                        parsed = urllib.parse.urlparse(clean_r_url)
                        q_vals = urllib.parse.parse_qs(parsed.query).get("q", [])
                        for q_val in q_vals:
                            target_link = urllib.parse.unquote(q_val).strip()
                            if target_link.startswith("http") and target_link.lower() not in seen_links:
                                seen_links.add(target_link.lower())
                                discovered_links.append(target_link)
                    except Exception:
                        pass

                direct_socials = re.findall(
                    r"https?:\/\/(?:www\.)?(?:instagram\.com|x\.com|twitter\.com|facebook\.com|fb\.com|twitch\.tv|discord\.gg|discord\.com\/invite|linkedin\.com|reddit\.com)\/[a-zA-Z0-9_\.\-]{1,50}",
                    resp.text,
                    re.IGNORECASE
                )
                for d_url in direct_socials:
                    d_url = d_url.rstrip(".,;)>\"'")
                    if d_url.lower() not in seen_links:
                        seen_links.add(d_url.lower())
                        discovered_links.append(d_url)

                if discovered_links:
                    break

            except Exception as e:
                logger.debug(f"Channel link scrape note for {t_url}: {e}")
                continue

    return {
        "channel_links": discovered_links,
        "scraped_description": discovered_description,
        "scraped_avatar": discovered_avatar
    }


async def fetch_via_youtube_api(target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetch video and channel data using official Google YouTube Data API v3 and channel link scraping."""
    if not settings.YOUTUBE_API_KEY:
        return None

    try:
        from googleapiclient.discovery import build
        
        youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY, cache_discovery=False)
        
        target_type = target.get("type")
        video_id = target.get("video_id")
        channel_id = target.get("channel_id")
        handle = target.get("handle")
        custom_name = target.get("custom_name")

        video_title = ""
        video_description = ""
        published_at = ""
        video_thumbnail = ""
        video_url = ""

        channel_name = ""
        channel_handle = handle
        channel_description = ""
        subscriber_count = None
        profile_image = None
        channel_url = target.get("channel_url")

        # ----------------------------------------------------------------------
        # Case A: Video target
        # ----------------------------------------------------------------------
        if target_type == "video" and video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
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
            video_description = snippet.get("description", "")
            published_at = snippet.get("publishedAt", "")
            thumbnails = snippet.get("thumbnails", {})
            video_thumbnail = (
                thumbnails.get("maxres", {}).get("url") or 
                thumbnails.get("high", {}).get("url") or 
                thumbnails.get("default", {}).get("url")
            )
            channel_name = snippet.get("channelTitle", "")

        # ----------------------------------------------------------------------
        # Fetch Channel Details (for both Video and Channel targets)
        # ----------------------------------------------------------------------
        channel_item = None

        if channel_id:
            c_resp = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=channel_id
            ).execute()
            c_items = c_resp.get("items", [])
            if c_items:
                channel_item = c_items[0]
        elif handle:
            c_resp = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                forHandle=handle.lstrip("@")
            ).execute()
            c_items = c_resp.get("items", [])
            if c_items:
                channel_item = c_items[0]
        elif custom_name:
            c_resp = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                forUsername=custom_name
            ).execute()
            c_items = c_resp.get("items", [])
            if c_items:
                channel_item = c_items[0]

        if channel_item:
            c_snippet = channel_item.get("snippet", {})
            c_stats = channel_item.get("statistics", {})
            c_branding = channel_item.get("brandingSettings", {}).get("channel", {})
            
            channel_id = channel_item.get("id", channel_id)
            channel_name = c_snippet.get("title", channel_name)
            raw_handle = c_snippet.get("customUrl")
            if raw_handle:
                channel_handle = raw_handle if raw_handle.startswith("@") else f"@{raw_handle}"
            
            # Extract channel description from snippet and brandingSettings
            channel_description = c_snippet.get("description", "") or c_branding.get("description", "")
            
            if channel_handle:
                channel_url = f"https://www.youtube.com/{channel_handle}"
            elif channel_id:
                channel_url = f"https://www.youtube.com/channel/{channel_id}"

            c_thumbs = c_snippet.get("thumbnails", {})
            profile_image = (
                c_thumbs.get("high", {}).get("url") or 
                c_thumbs.get("medium", {}).get("url") or 
                video_thumbnail
            )
            
            subs = c_stats.get("subscriberCount")
            if subs:
                subscriber_count = format_subscribers(int(subs))

        # ----------------------------------------------------------------------
        # Scrape channel page for external Links (Instagram, X, etc.)
        # ----------------------------------------------------------------------
        channel_links = []
        try:
            scraped_info = await scrape_channel_links_and_about(
                channel_handle=channel_handle,
                channel_id=channel_id,
                channel_url=channel_url
            )
            channel_links = scraped_info.get("channel_links", [])
            if not channel_description and scraped_info.get("scraped_description"):
                channel_description = scraped_info.get("scraped_description")
            if not profile_image and scraped_info.get("scraped_avatar"):
                profile_image = scraped_info.get("scraped_avatar")
        except Exception as e:
            logger.debug(f"Channel link scrape note: {e}")

        # ----------------------------------------------------------------------
        # If target was Channel directly, fetch latest video for context
        # ----------------------------------------------------------------------
        recent_video_descriptions = []
        if channel_id:
            try:
                search_resp = youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    type="video",
                    order="date",
                    maxResults=3
                ).execute()
                search_items = search_resp.get("items", [])
                
                if search_items and not video_id:
                    top_video = search_items[0]
                    video_id = top_video.get("id", {}).get("videoId")
                    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
                    video_title = top_video.get("snippet", {}).get("title", "")
                    video_description = top_video.get("snippet", {}).get("description", "")
                    video_thumbnail = top_video.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url")
                    published_at = top_video.get("snippet", {}).get("publishedAt", "")

                for item in search_items:
                    s_desc = item.get("snippet", {}).get("description", "")
                    if s_desc and s_desc not in recent_video_descriptions:
                        recent_video_descriptions.append(s_desc)
            except Exception as e:
                logger.debug(f"Note: Could not fetch recent videos: {e}")

        # ----------------------------------------------------------------------
        # Combine descriptions so email and social discovery search all sources
        # ----------------------------------------------------------------------
        desc_sections = []
        if channel_description:
            desc_sections.append(f"--- Channel About / Description ---\n{channel_description}")
        if channel_links:
            desc_sections.append(f"--- Channel Links ---\n" + "\n".join(channel_links))
        if video_description:
            desc_sections.append(f"--- Video Description ---\n{video_description}")
        for idx, r_desc in enumerate(recent_video_descriptions, 1):
            if r_desc != video_description:
                desc_sections.append(f"--- Recent Video Description #{idx} ---\n{r_desc}")

        combined_description = "\n\n".join(desc_sections) if desc_sections else (channel_description or video_description or "")

        final_handle = channel_handle or f"@{channel_name.lower().replace(' ', '')}"
        final_channel_url = channel_url or f"https://www.youtube.com/{final_handle}"

        return {
            "video_id": video_id or "channel_view",
            "video_title": video_title or f"{channel_name} Channel",
            "creator_name": channel_name or "Creator",
            "channel_name": channel_name or "Channel",
            "channel_handle": final_handle,
            "channel_url": final_channel_url,
            "profile_image": profile_image or video_thumbnail,
            "subscriber_count": subscriber_count or "Subscribers unavailable",
            "video_url": video_url or final_channel_url,
            "description": combined_description,
            "channel_description": channel_description,
            "video_description": video_description,
            "channel_links": channel_links,
            "published_at": published_at,
            "source": "official_youtube_api"
        }
    except Exception as e:
        logger.error(f"Error fetching from YouTube API: {e}", exc_info=True)
        return None


async def fetch_via_public_fallback(target: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback YouTube extractor using YouTube oEmbed, watch page, and channel page scraping."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    target_type = target.get("type")
    video_id = target.get("video_id")
    handle = target.get("handle")
    channel_url = target.get("channel_url")

    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else (channel_url or target.get("raw", ""))
    video_title = ""
    video_description = ""
    creator_name = ""
    channel_handle = handle
    channel_description = ""
    profile_image = None
    subscriber_count = None
    channel_links = []

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
        # 1. If Video ID present: fetch oEmbed and Watch page
        if target_type == "video" and video_id:
            # oEmbed
            oembed_url = f"https://www.youtube.com/oembed?url={video_url}&format=json"
            try:
                resp = await client.get(oembed_url)
                if resp.status_code == 200:
                    oembed_data = resp.json()
                    video_title = oembed_data.get("title", "")
                    creator_name = oembed_data.get("author_name", "")
                    author_url = oembed_data.get("author_url", "")
                    if author_url and not channel_url:
                        channel_url = author_url
                    profile_image = oembed_data.get("thumbnail_url")
            except Exception as e:
                logger.warning(f"oEmbed fetch failed for {video_id}: {e}")

            # Watch page HTML
            try:
                html_resp = await client.get(video_url)
                if html_resp.status_code == 200:
                    soup = BeautifulSoup(html_resp.text, "html.parser")
                    if not video_title:
                        meta_title = soup.find("meta", property="og:title")
                        video_title = meta_title["content"] if meta_title and meta_title.get("content") else f"YouTube Video ({video_id})"

                    # 1. First priority: Extract full un-truncated description from ytInitialPlayerResponse
                    m_player = re.search(r"var ytInitialPlayerResponse = ({.*?});(?:var|const|let|<\/script>)", html_resp.text)
                    if m_player:
                        try:
                            player_data = json.loads(m_player.group(1))
                            vd = player_data.get("videoDetails", {})
                            if vd.get("shortDescription"):
                                video_description = vd["shortDescription"]
                            if not creator_name and vd.get("author"):
                                creator_name = vd["author"]
                            if not video_title and vd.get("title"):
                                video_title = vd["title"]
                            if not channel_url and vd.get("channelId"):
                                channel_url = f"https://www.youtube.com/channel/{vd['channelId']}"
                        except Exception as e:
                            logger.debug(f"ytInitialPlayerResponse parse note: {e}")

                    # 2. Second priority: Search ytInitialData for description and subscriber count
                    m = re.search(r"var ytInitialData = ({.*?});</script>", html_resp.text)
                    if m:
                        try:
                            yt_data = json.loads(m.group(1))

                            if not video_description:
                                def find_desc(obj):
                                    if isinstance(obj, dict):
                                        if "shortDescription" in obj and isinstance(obj["shortDescription"], str) and obj["shortDescription"]:
                                            return obj["shortDescription"]
                                        for v in obj.values():
                                            res = find_desc(v)
                                            if res:
                                                return res
                                    elif isinstance(obj, list):
                                        for item in obj:
                                            res = find_desc(item)
                                            if res:
                                                return res
                                    return None
                                full_desc = find_desc(yt_data)
                                if full_desc:
                                    video_description = full_desc

                            # Look for subscriber count
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

                            for sub_text in find_key(yt_data, "subscriberCountText"):
                                if isinstance(sub_text, dict) and "simpleText" in sub_text:
                                    subscriber_count = sub_text["simpleText"]
                                    break
                                elif isinstance(sub_text, dict) and "runs" in sub_text:
                                    subscriber_count = "".join(r.get("text", "") for r in sub_text["runs"])
                                    break
                        except Exception as e:
                            logger.debug(f"ytInitialData parse note: {e}")

                    # 3. Fallback: meta tag description (which YouTube truncates to ~150 chars)
                    if not video_description:
                        meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                        if meta_desc and meta_desc.get("content"):
                            video_description = meta_desc["content"]

                    if not channel_url:
                        author_link = soup.find("link", itemprop="url")
                        if author_link and author_link.get("href"):
                            channel_url = author_link["href"]
            except Exception as e:
                logger.debug(f"Watch page scrape error: {e}")

        # Resolve creator and channel identity before scraping channel links
        channel_name = creator_name or "YouTube Creator"
        if not channel_handle:
            if channel_url and "@" in channel_url:
                channel_handle = "@" + channel_url.split("@")[-1].split("/")[0]
            else:
                channel_handle = f"@{channel_name.lower().replace(' ', '')}"

        # 2. Scrape Channel Page (About / Links / Metadata)
        try:
            scraped_info = await scrape_channel_links_and_about(
                channel_handle=channel_handle,
                channel_url=channel_url
            )
            channel_links = scraped_info.get("channel_links", [])
            if not channel_description and scraped_info.get("scraped_description"):
                channel_description = scraped_info.get("scraped_description")
            if not profile_image and scraped_info.get("scraped_avatar"):
                profile_image = scraped_info.get("scraped_avatar")
        except Exception as e:
            logger.debug(f"Channel scrape note: {e}")

        desc_sections = []
        if channel_description:
            desc_sections.append(f"--- Channel About / Description ---\n{channel_description}")
        if channel_links:
            desc_sections.append(f"--- Channel Links ---\n" + "\n".join(channel_links))
        if video_description:
            desc_sections.append(f"--- Video Description ---\n{video_description}")
        combined_description = "\n\n".join(desc_sections) if desc_sections else (channel_description or video_description or "No description provided.")

        return {
            "video_id": video_id or "channel_view",
            "video_title": video_title or f"{channel_name} Channel",
            "creator_name": channel_name,
            "channel_name": channel_name,
            "channel_handle": channel_handle,
            "channel_url": channel_url or f"https://www.youtube.com/{channel_handle}",
            "profile_image": profile_image or f"https://ui-avatars.com/api/?name={channel_name}&background=00D26A&color=000&bold=true",
            "subscriber_count": subscriber_count or "Active Creator",
            "video_url": video_url,
            "description": combined_description,
            "channel_description": channel_description,
            "video_description": video_description,
            "channel_links": channel_links,
            "published_at": None,
            "source": "public_fallback_extractor"
        }


async def get_youtube_metadata(url: str) -> Dict[str, Any]:
    """Main entrypoint for YouTube metadata extraction.
    
    Validates URL or handle, tries YouTube Data API v3, and falls back gracefully.
    """
    target = parse_youtube_target(url)
    if target.get("type") == "unknown":
        raise ValueError(f"Could not parse a valid YouTube video or channel from URL: {url}")

    # Try official API if key provided
    if settings.YOUTUBE_API_KEY:
        data = await fetch_via_youtube_api(target)
        if data:
            return data

    # Use public resilient fallback
    return await fetch_via_public_fallback(target)
