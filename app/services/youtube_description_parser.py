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
    r"\b(?:contributor|contributors|collaborator|collaborators|collab|collaboration|credit|credits|credited|"
    r"edited by|editor|video editor|video edit|edit by|edit|vfx by|vfx|visual effects|thumbnail by|thumbnail|thumbnail artist|"
    r"thumb by|thumb|sound by|sound designer|sound|audio by|audio engineer|audio|music by|music|written by|writer|script by|"
    r"assisted by|assistant by|assistant|assisted)\b"
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

    # Strategy 4: Candidate accounts extracted via explicit credit detection
    for c in extract_credit_candidates(description):
        add_candidate(c["username"])

    return discovered_usernames


def is_credit_role_matching(credit_role: str, user_role: Optional[str]) -> bool:
    """Check if an explicit credit role in the description matches the user's selected role."""
    if not user_role or not user_role.strip():
        # If user didn't specify a role, any explicit credit role is allowed
        return True

    c_role = (credit_role or "").strip().lower()
    u_role = user_role.strip().lower()

    # Generic credit roles match any user role (e.g., "Credits: @user", "Contributor: @user", "Assisted by @user")
    generic_roles = {
        "credit", "credits", "credited", "contributor", "contributors",
        "collaborator", "collaborators", "collab", "collaboration",
        "assisted", "assistant", "team", "special thanks", "thanks to", "thanks"
    }
    if any(gr in c_role for gr in generic_roles):
        return True

    # Editorial roles
    editor_terms = ["edit", "editor", "edited", "video edit", "video editor", "cut", "cutter", "cutting", "assembly"]
    is_user_editor = any(t in u_role for t in editor_terms)
    is_credit_editor = any(t in c_role for t in editor_terms)
    if is_user_editor:
        return is_credit_editor

    # Thumbnail roles
    thumb_terms = ["thumb", "thumbnail", "cover art", "cover", "graphic", "designer"]
    is_user_thumb = any(t in u_role for t in thumb_terms)
    is_credit_thumb = any(t in c_role for t in thumb_terms)
    if is_user_thumb:
        return is_credit_thumb

    # VFX / Motion Graphics
    vfx_terms = ["vfx", "visual effects", "fx", "effect", "motion", "animation", "animator", "cgi", "compositor"]
    is_user_vfx = any(t in u_role for t in vfx_terms)
    is_credit_vfx = any(t in c_role for t in vfx_terms)
    if is_user_vfx:
        return is_credit_vfx

    # Audio / Sound / Music
    audio_terms = ["sound", "audio", "music", "score", "mix", "master", "composer"]
    is_user_audio = any(t in u_role for t in audio_terms)
    is_credit_audio = any(t in c_role for t in audio_terms)
    if is_user_audio:
        return is_credit_audio

    # Writer / Script
    writer_terms = ["writer", "written", "script", "screenplay"]
    is_user_writer = any(t in u_role for t in writer_terms)
    is_credit_writer = any(t in c_role for t in writer_terms)
    if is_user_writer:
        return is_credit_writer

    # Direct substring / overlap match
    return c_role in u_role or u_role in c_role


CREDIT_ROLE_PATTERN = re.compile(
    r"\b(contributor|contributors|collaborator|collaborators|collab|collaboration|credit|credits|credited|"
    r"edited by|editor|video editor|video edit|edit by|edits by|edit|edits|cut by|cuts by|cutting|"
    r"vfx by|vfx|visual effects|visual effect|thumbnail by|thumbnail|thumbnail artist|thumbnail designer|thumb by|thumb|"
    r"sound by|sound designer|sound design|sound|audio by|audio engineer|audio|music by|music|written by|writer|script by|"
    r"assisted by|assistant by|assistant|assisted)\b"
    r"(?:\s*[\(\[](?:instagram|insta|ig|twitter|x|twitch|facebook|fb|discord|youtube)[\)\]])?"
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

CREDIT_LINE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:special\s+thanks\s+to\s+our\s+|thanks\s+to\s+our\s+|special\s+thanks\s+to\s+|thanks\s+to\s+|thanks\s+|)("
    r"contributor|contributors|collaborator|collaborators|collab|collaboration|credit|credits|credited|"
    r"edited by|editor|video editor|video edit|edit by|edits by|edit|edits|cut by|cuts by|cutting|"
    r"vfx by|vfx|visual effects|visual effect|thumbnail by|thumbnail|thumbnail artist|thumbnail designer|thumb by|thumb|"
    r"sound by|sound designer|sound design|sound|audio by|audio engineer|audio|music by|music|written by|writer|script by|"
    r"assisted by|assistant by|assistant|assisted"
    r")(?:\s*[\(\[](?:instagram|insta|ig|twitter|x|twitch|facebook|fb|discord|youtube)[\)\]])?\s*[\:\-\—\|\–\>\•\*\~]+\s*(.*)$",
    re.IGNORECASE
)

REVERSE_CREDIT_PATTERN = re.compile(
    r"@([a-zA-Z0-9_\.]{2,30})\s+(?:was\s+the\s+|is\s+the\s+|worked\s+as\s+)?(editor|video editor|thumbnail designer|vfx artist|creator|collaborator|contributor|assisted|collaborated|edited)\b",
    re.IGNORECASE
)

# Regex to detect name-first credits (e.g. "DRNKIE: Thumbnail", "Badogblue: Editor/Gameplay", "Trenton Oliver: Video Editor")
NAME_FIRST_CREDIT_REGEX = re.compile(
    r"^\s*([A-Za-z0-9_\.\s]{2,40}?)\s*[\:\-\—\|\–]\s*"
    r"((?:[a-zA-Z\s]+[\/])*(?:editor|video editor|video edit|edit|edits|cut|cutting|cutter|"
    r"thumbnail|thumbnail artist|thumbnail designer|thumb|"
    r"vfx|vfx artist|visual effects|motion graphics|animator|animation|"
    r"sound designer|sound design|sound|audio engineer|audio|music|score|composer|"
    r"writer|script|director|colorist)(?:[\/][a-zA-Z\s]+)*)\s*$",
    re.IGNORECASE
)

# Regex to detect role-first plain human name credits (e.g. "Edited by Trenton Oliver", "Editor: Trenton Oliver")
ROLE_FIRST_NAME_REGEX = re.compile(
    r"(?i:\b(edited by|editor|video editor|video edit|edit by|edits by|cut by|cuts by|"
    r"thumbnail by|thumbnail artist|thumbnail designer|thumbnail|thumb by|thumb|"
    r"vfx by|vfx artist|vfx|visual effects by|visual effects|"
    r"sound design by|sound designer|sound by|audio by|music by|"
    r"written by|writer|script by)\b)"
    r"[ \t\:\-\—\|\–\>\•\*\~]*[^\w\s@\/]*[ \t\:\-\—\|\–\>\•\*\~]*"
    r"([A-Z][a-zA-Z0-9_\.]*(?:[ \t]+[A-Z][a-zA-Z0-9_\.]*){1,3})\b"
)

NAME_EXCLUDE_WORDS: Set[str] = {
    "the", "our", "this", "video", "channel", "team", "everyone",
    "youtube", "instagram", "twitter", "twitch", "tiktok", "facebook",
    "discord", "link", "special", "check", "subscribe", "song", "music",
    "production", "productions", "courtesy", "records", "stream", "vote"
}


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


def extract_credit_candidates(
    description: Optional[str],
    user_role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Extract candidate usernames and their associated role/credit labels from a description.
    
    Strictly extracts explicit credits only (e.g. 'Editor: @user', 'Contributors: @user1 @user2',
    'DRNKIE: Thumbnail', 'Edited by Trenton Oliver').
    Filters candidates according to whether the credit role matches user_role.
    Standalone or promotional @mentions without explicit credit indicators are never extracted.
    
    Returns:
        List of dicts: [
            {"username": "ummer.04", "role": "editor", "specified_platform": None, "is_name": False},
            {"username": "Trenton Oliver", "role": "editor", "display_name": "Trenton Oliver", "is_name": True}
        ]
    """
    if not description or not description.strip():
        return []

    raw_text = urllib.parse.unquote(description)
    results: List[Dict[str, Any]] = []
    seen_keys: Set[str] = set()

    def get_norm_key(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", name or "").lower()

    # Strategy A: Match inline credit role patterns (e.g. "Editor: @ummer.04", "thumbnail by @cool_thumb")
    for match in CREDIT_ROLE_PATTERN.finditer(raw_text):
        role_label = (match.group(1) or "credit").lower()

        if not is_credit_role_matching(role_label, user_role):
            continue

        handle = None
        for g in match.groups()[1:]:
            if g:
                handle = clean_and_normalize_username(g)
                if handle:
                    break

        if handle:
            key = get_norm_key(handle)
            if key and key not in seen_keys:
                seen_keys.add(key)
                start_idx = max(0, raw_text.rfind("\n", 0, match.start()))
                end_idx = raw_text.find("\n", match.end())
                if end_idx == -1:
                    end_idx = len(raw_text)
                line_context = raw_text[start_idx:end_idx]
                specified_platform = detect_specified_platform(line_context)

                results.append({
                    "username": handle,
                    "display_name": handle,
                    "role": role_label,
                    "specified_platform": specified_platform,
                    "is_name": False
                })

    # Strategy B: Line-based credit lists, e.g. "Contributors: @john_doe @ummer.04 @alex123"
    lines = raw_text.splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_match = CREDIT_LINE_PREFIX_PATTERN.match(line_clean)
        if line_match:
            role_label = (line_match.group(1) or "credit").lower()
            if not is_credit_role_matching(role_label, user_role):
                continue
            rest = line_match.group(2)
            specified_platform = detect_specified_platform(line_clean)
            for at_match in AT_MENTION_REGEX.finditer(rest):
                h = clean_and_normalize_username(at_match.group(1))
                if h:
                    key = get_norm_key(h)
                    if key and key not in seen_keys:
                        seen_keys.add(key)
                        results.append({
                            "username": h,
                            "display_name": h,
                            "role": role_label,
                            "specified_platform": specified_platform,
                            "is_name": False
                        })

    # Strategy C: Reverse credit mentions (e.g. "@UMMER.04 was the editor on this video")
    for match in REVERSE_CREDIT_PATTERN.finditer(raw_text):
        h = clean_and_normalize_username(match.group(1))
        role_label = (match.group(2) or "editor").lower()
        if not is_credit_role_matching(role_label, user_role):
            continue
        if h:
            key = get_norm_key(h)
            if key and key not in seen_keys:
                seen_keys.add(key)
                start_idx = max(0, raw_text.rfind("\n", 0, match.start()))
                end_idx = raw_text.find("\n", match.end())
                if end_idx == -1:
                    end_idx = len(raw_text)
                line_context = raw_text[start_idx:end_idx]
                specified_platform = detect_specified_platform(line_context)
                results.append({
                    "username": h,
                    "display_name": h,
                    "role": role_label,
                    "specified_platform": specified_platform,
                    "is_name": False
                })

    # Strategy D: Name-first credits (e.g. "DRNKIE: Thumbnail", "Badogblue: Editor/Gameplay")
    social_line_re = re.compile(
        r"^\s*(?:(?:\[\s*)?(YouTube|Twitter|Twitch|Instagram|Discord|Facebook|TikTok)(?:\s*\])?)\s*[:\-\—]?\s*(.*)$",
        re.IGNORECASE
    )
    handle_re = re.compile(r"(?:https?:\/\/[^\s]+[\/=]|@|\/\s*)([a-zA-Z0-9_\.]{2,30})", re.IGNORECASE)

    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        m = NAME_FIRST_CREDIT_REGEX.match(line_clean)
        if m:
            name_part = m.group(1).strip()
            role_label = m.group(2).strip().lower()

            # Reject common excluded headers or titles
            lower_name = name_part.lower()
            if any(w in lower_name for w in ["stream", "vote", "follow", "who is", "thanks", "everyone", "involved"]):
                continue

            if not is_credit_role_matching(role_label, user_role):
                continue

            # Look ahead in subsequent lines for social links associated with this person
            known_socials: Dict[str, str] = {}
            best_handle = None
            for sub_idx in range(idx + 1, min(len(lines), idx + 8)):
                sub_line = lines[sub_idx].strip()
                if not sub_line or NAME_FIRST_CREDIT_REGEX.match(sub_line):
                    break
                sm = social_line_re.match(sub_line)
                if sm:
                    plat = sm.group(1).capitalize()
                    if plat.lower() == "twitter":
                        plat = "Twitter"
                    rest = sm.group(2)
                    hm = handle_re.search(rest)
                    if hm:
                        clean_h = clean_and_normalize_username(hm.group(1))
                        if clean_h:
                            known_socials[plat] = clean_h
                            if not best_handle:
                                best_handle = clean_h

            is_human_name = " " in name_part.strip()
            final_user = best_handle or (clean_and_normalize_username(name_part) or name_part)
            key = get_norm_key(final_user)
            if key and key not in seen_keys:
                seen_keys.add(key)
                results.append({
                    "username": final_user,
                    "display_name": name_part,
                    "role": role_label,
                    "specified_platform": "Instagram" if "Instagram" in known_socials else (list(known_socials.keys())[0] if known_socials else None),
                    "known_platforms": known_socials,
                    "is_name": is_human_name
                })

    # Strategy E: Role-first plain human name credits (e.g. "Edited by Trenton Oliver", "Editor: Trenton Oliver")
    for m in ROLE_FIRST_NAME_REGEX.finditer(raw_text):
        role_label = m.group(1).strip().lower()
        raw_name = m.group(2).strip()

        if not is_credit_role_matching(role_label, user_role):
            continue

        words = [w.lower() for w in raw_name.split()]
        if any(w in NAME_EXCLUDE_WORDS for w in words):
            continue

        key = get_norm_key(raw_name)
        if key and key not in seen_keys:
            seen_keys.add(key)
            results.append({
                "username": raw_name,
                "display_name": raw_name,
                "role": role_label,
                "specified_platform": None,
                "is_name": True
            })

    return results


async def extract_verified_contributor_accounts(
    description: Optional[str],
    linked_platform: Optional[str] = None,
    linked_account: Optional[str] = None,
    user_role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Extract credit candidate usernames and verify which platforms they exist on.
    
    Filters candidates to only explicit credits matching user_role.
    Strictly verifies candidate existence on target platforms before including them.
    If a username does not exist on the platform, it is omitted.
    Human names (is_name=True) are preserved directly for auto-verification.
    
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
    candidates = extract_credit_candidates(description, user_role=user_role)
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
            is_name = cand.get("is_name", False)
            display_name = cand.get("display_name") or username
            specified = cand.get("specified_platform")
            known_platforms = cand.get("known_platforms", {})

            # Plain human names (e.g. "Trenton Oliver"): preserve directly for user connection & auto-verification
            if is_name:
                verified_list.append({
                    "username": display_name,
                    "display_name": display_name,
                    "role": role,
                    "is_name": True,
                    "platforms": ["Instagram"],
                    "urls": {}
                })
                continue

            existing_platforms: List[str] = []
            urls: Dict[str, str] = {}

            if known_platforms:
                for p, h in known_platforms.items():
                    plat_name = p.capitalize()
                    if plat_name.lower() == "twitter":
                        plat_name = "Twitter"
                    existing_platforms.append(plat_name)
                    urls[plat_name] = f"https://{plat_name.lower()}.com/{h}"

            # Determine target platforms to check
            if specified:
                target_platforms = [specified]
            elif eff_platform:
                target_platforms = [eff_platform]
            else:
                target_platforms = ["Instagram", "X", "Facebook", "Twitch", "Discord"]

            needed_checks = [p for p in target_platforms if p not in existing_platforms]
            if needed_checks:
                plat_results = await verify_username_on_platforms(
                    username, client=client, platforms=needed_checks
                )
                for p, exists in plat_results.items():
                    if exists:
                        existing_platforms.append(p)
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

            # Candidate exists on at least one platform (or has known platforms in description)
            if existing_platforms:
                verified_list.append({
                    "username": username,
                    "display_name": display_name,
                    "role": role,
                    "platforms": existing_platforms,
                    "urls": urls
                })

    return verified_list


