"""LangGraph orchestration graph for Creator Discovery & Intelligence."""

import logging
from typing import TypedDict, List, Optional, Dict, Any, AsyncGenerator
from langgraph.graph import StateGraph, START, END

from app.models.schemas import SocialProfile, EmailCandidate, RawCreatorResearchResult
from app.services.youtube_service import parse_youtube_target, extract_video_id, get_youtube_metadata
from app.services.social_discovery import extract_social_profiles, extract_website_urls, rank_social_profiles
from app.services.email_discovery import extract_emails_from_text, crawl_website_for_emails
from app.services.mistral_service import classify_and_verify_with_mistral

logger = logging.getLogger(__name__)

ALLOWED_PLATFORMS = {"Instagram", "X", "X/Twitter", "Discord", "Reddit", "Facebook"}


class CreatorResearchState(TypedDict):
    """LangGraph state representation for creator intelligence workflow."""
    video_url: str
    video_id: Optional[str]
    channel_id: Optional[str]
    creator_name: Optional[str]
    channel_name: Optional[str]
    channel_handle: Optional[str]
    channel_url: Optional[str]
    profile_image: Optional[str]
    video_title: Optional[str]
    subscriber_count: Optional[str]
    description: Optional[str]
    channel_description: Optional[str]
    video_description: Optional[str]
    channel_links: List[str]
    published_at: Optional[str]
    social_profiles: List[Dict[str, Any]]
    email_candidates: List[Dict[str, Any]]
    selected_email: Optional[str]
    email_source: Optional[str]
    email_confidence: Optional[str]
    email_source_type: Optional[str]
    errors: List[str]
    current_step: Optional[str]


# ------------------------------------------------------------------------------
# Workflow Nodes
# ------------------------------------------------------------------------------

async def validate_url_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 1: Validate YouTube URL and extract video ID or channel handle."""
    url = state.get("video_url", "").strip()
    target = parse_youtube_target(url)
    
    if target.get("type") == "unknown":
        return {
            "current_step": "validate_url",
            "errors": state.get("errors", []) + [f"Invalid YouTube URL: {url}"]
        }
    
    return {
        "video_id": target.get("video_id"),
        "channel_handle": target.get("handle"),
        "channel_id": target.get("channel_id"),
        "current_step": "validate_url"
    }


async def fetch_youtube_metadata_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 2: Fetch video & channel metadata from YouTube API or resilient fallback."""
    if state.get("errors"):
        return state

    url = state["video_url"]
    try:
        data = await get_youtube_metadata(url)
        return {
            "video_id": data.get("video_id") or state.get("video_id"),
            "video_title": data.get("video_title"),
            "video_url": data.get("video_url") or state.get("video_url"),
            "creator_name": data.get("creator_name"),
            "channel_name": data.get("channel_name"),
            "channel_handle": data.get("channel_handle") or state.get("channel_handle"),
            "channel_url": data.get("channel_url"),
            "profile_image": data.get("profile_image"),
            "subscriber_count": data.get("subscriber_count"),
            "description": data.get("description", ""),
            "channel_description": data.get("channel_description", ""),
            "video_description": data.get("video_description", ""),
            "channel_links": data.get("channel_links", []),
            "published_at": data.get("published_at"),
            "current_step": "fetch_metadata"
        }
    except Exception as e:
        logger.error(f"Error in fetch_youtube_metadata_node: {e}", exc_info=True)
        return {
            "current_step": "fetch_metadata",
            "errors": state.get("errors", []) + [f"Failed to retrieve video metadata: {str(e)}"]
        }


async def identify_creator_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 3: Process channel and creator identity branding."""
    if state.get("errors"):
        return state

    creator_name = state.get("creator_name") or state.get("channel_name") or "Creator"
    handle = state.get("channel_handle")
    if not handle:
        handle = f"@{creator_name.lower().replace(' ', '')}"

    return {
        "creator_name": creator_name,
        "channel_handle": handle,
        "current_step": "identify_creator"
    }


async def discover_socials_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 4: Discover public social media profiles strictly for Instagram, X, Discord, Reddit, Facebook."""
    if state.get("errors"):
        return state

    channel_links = state.get("channel_links", [])
    channel_desc = state.get("channel_description", "")
    video_desc = state.get("video_description", "")
    full_desc = state.get("description", "")

    all_socials: List[SocialProfile] = []
    seen_keys = set()

    # 1. Search channel links first (e.g. from YouTube Links section)
    if channel_links:
        links_text = "\n".join(channel_links)
        for s in extract_social_profiles(links_text, source_label="YouTube Channel Links"):
            key = (s.platform, s.url.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                all_socials.append(s)

    # 2. Search channel description
    if channel_desc:
        for s in extract_social_profiles(channel_desc, source_label="YouTube Channel Description"):
            key = (s.platform, s.url.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                all_socials.append(s)

    # 3. Search video description
    if video_desc:
        for s in extract_social_profiles(video_desc, source_label="YouTube Video Description"):
            key = (s.platform, s.url.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                all_socials.append(s)

    # 4. Search full description
    if full_desc:
        for s in extract_social_profiles(full_desc, source_label="YouTube Description"):
            key = (s.platform, s.url.lower())
            if key not in seen_keys:
                seen_keys.add(key)
                all_socials.append(s)

    # Strictly filter allowed platforms and rank by authenticity
    ranked_socials = rank_social_profiles(
        all_socials,
        creator_name=state.get("creator_name", ""),
        channel_name=state.get("channel_name", ""),
        channel_handle=state.get("channel_handle", "")
    )

    filtered_socials = [
        s.model_dump() for s in ranked_socials 
        if s.platform in ALLOWED_PLATFORMS
    ]
    
    return {
        "social_profiles": filtered_socials,
        "current_step": "discover_socials"
    }


async def discover_emails_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 5: Discover candidate public emails from channel description, video description, and website."""
    if state.get("errors"):
        return state

    channel_desc = state.get("channel_description", "")
    video_desc = state.get("video_description", "")
    full_desc = state.get("description", "")
    channel_links = state.get("channel_links", [])
    
    email_candidates: List[EmailCandidate] = []
    seen_emails = set()

    # 1. Search Channel Description (High priority for business contact)
    if channel_desc:
        c_emails = extract_emails_from_text(channel_desc, source_label="YouTube Channel Description")
        for e in c_emails:
            if e.email.lower() not in seen_emails:
                seen_emails.add(e.email.lower())
                email_candidates.append(e)

    # 2. Search Video Description
    if video_desc:
        v_emails = extract_emails_from_text(video_desc, source_label="YouTube Video Description")
        for e in v_emails:
            if e.email.lower() not in seen_emails:
                seen_emails.add(e.email.lower())
                email_candidates.append(e)

    # 3. Search Full Combined Description if needed
    if full_desc:
        f_emails = extract_emails_from_text(full_desc, source_label="YouTube Description")
        for e in f_emails:
            if e.email.lower() not in seen_emails:
                seen_emails.add(e.email.lower())
                email_candidates.append(e)

    # 4. Check if personal website URLs exist to crawl contact pages
    all_text_for_sites = f"{channel_desc}\n{video_desc}\n{full_desc}\n" + "\n".join(channel_links)
    website_urls = extract_website_urls(all_text_for_sites)
    
    for site_url in website_urls[:2]:  # Limit to 2 websites max for speed
        if site_url:
            try:
                site_emails = await crawl_website_for_emails(site_url)
                for e in site_emails:
                    if e.email.lower() not in seen_emails:
                        seen_emails.add(e.email.lower())
                        email_candidates.append(e)
            except Exception as e:
                logger.debug(f"Website crawl error for {site_url}: {e}")

    unique_candidates = [c.model_dump() for c in email_candidates]

    return {
        "email_candidates": unique_candidates,
        "current_step": "discover_emails"
    }


async def classify_and_finalize_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 6: Classify email evidence and finalize creator intelligence profile."""
    if state.get("errors"):
        return state

    creator_name = state.get("creator_name", "")
    channel_name = state.get("channel_name", "")
    video_title = state.get("video_title", "")
    description = state.get("description", "")
    channel_description = state.get("channel_description", "")
    video_description = state.get("video_description", "")
    
    raw_socials = [
        SocialProfile(**s) for s in state.get("social_profiles", [])
        if s.get("platform") in ALLOWED_PLATFORMS
    ]
    raw_emails = [EmailCandidate(**e) for e in state.get("email_candidates", [])]

    # Try Mistral AI reasoning
    mistral_result = await classify_and_verify_with_mistral(
        creator_name=creator_name,
        channel_name=channel_name,
        video_title=video_title,
        description=description,
        raw_socials=raw_socials,
        raw_emails=raw_emails,
        channel_description=channel_description,
        video_description=video_description
    )

    selected_email = None
    email_source = None
    email_confidence = None
    email_source_type = None

    if mistral_result and mistral_result.selected_primary_email:
        # Match with classified email
        selected_email = mistral_result.selected_primary_email
        for c in raw_emails:
            if c.email.lower() == selected_email.lower():
                email_source = c.source
                email_confidence = c.confidence
                email_source_type = c.source_type
                break
        if not email_source:
            email_source = "YouTube Channel Description" if channel_description and selected_email.lower() in channel_description.lower() else "Verified via Mistral AI Analysis"
            email_confidence = "high"
            email_source_type = "publicly_published"

    # Deterministic fallback if Mistral is not configured or returned no primary email
    if not selected_email and raw_emails:
        # Prioritize 'high' confidence publicly published emails
        public_high = [e for e in raw_emails if e.confidence == "high" and e.source_type == "publicly_published"]
        if public_high:
            chosen = public_high[0]
            selected_email = chosen.email
            email_source = chosen.source
            email_confidence = chosen.confidence
            email_source_type = chosen.source_type
        else:
            # Pick first publicly published candidate
            public_any = [e for e in raw_emails if e.source_type == "publicly_published"]
            if public_any:
                chosen = public_any[0]
                selected_email = chosen.email
                email_source = chosen.source
                email_confidence = chosen.confidence
                email_source_type = chosen.source_type

    # Merge Mistral verified socials with regex discovered socials
    final_socials = list(state.get("social_profiles", []))
    seen_social_urls = {s.get("url", "").lower() for s in final_socials}

    if mistral_result and mistral_result.verified_socials:
        for v_soc in mistral_result.verified_socials:
            v_plat = v_soc.get("platform", "")
            v_user = v_soc.get("username", "")
            v_url = v_soc.get("url", "")
            if v_plat in ALLOWED_PLATFORMS and v_url and v_url.lower() not in seen_social_urls:
                seen_social_urls.add(v_url.lower())
                final_socials.append({
                    "platform": v_plat,
                    "username": v_user,
                    "url": v_url,
                    "source": "Verified via Mistral AI Analysis",
                    "confidence": v_soc.get("confidence", "high")
                })

    return {
        "selected_email": selected_email,
        "email_source": email_source,
        "email_confidence": email_confidence,
        "email_source_type": email_source_type,
        "social_profiles": final_socials,
        "current_step": "finalize"
    }


# ------------------------------------------------------------------------------
# Graph Construction
# ------------------------------------------------------------------------------

def build_creator_research_graph() -> StateGraph:
    """Build the compiled LangGraph workflow graph."""
    workflow = StateGraph(CreatorResearchState)

    # Add Nodes
    workflow.add_node("validate_url", validate_url_node)
    workflow.add_node("fetch_metadata", fetch_youtube_metadata_node)
    workflow.add_node("identify_creator", identify_creator_node)
    workflow.add_node("discover_socials", discover_socials_node)
    workflow.add_node("discover_emails", discover_emails_node)
    workflow.add_node("classify_and_finalize", classify_and_finalize_node)

    # Add Edges
    workflow.add_edge(START, "validate_url")
    workflow.add_edge("validate_url", "fetch_metadata")
    workflow.add_edge("fetch_metadata", "identify_creator")
    workflow.add_edge("identify_creator", "discover_socials")
    workflow.add_edge("discover_socials", "discover_emails")
    workflow.add_edge("discover_emails", "classify_and_finalize")
    workflow.add_edge("classify_and_finalize", END)

    return workflow.compile()


research_graph = build_creator_research_graph()


# ------------------------------------------------------------------------------
# Execution Helpers
# ------------------------------------------------------------------------------

async def execute_creator_research(youtube_url: str) -> RawCreatorResearchResult:
    """Execute the complete LangGraph research pipeline."""
    initial_state: CreatorResearchState = {
        "video_url": youtube_url,
        "video_id": None,
        "channel_id": None,
        "creator_name": None,
        "channel_name": None,
        "channel_handle": None,
        "channel_url": None,
        "profile_image": None,
        "video_title": None,
        "subscriber_count": None,
        "description": None,
        "channel_description": None,
        "video_description": None,
        "channel_links": [],
        "published_at": None,
        "social_profiles": [],
        "email_candidates": [],
        "selected_email": None,
        "email_source": None,
        "email_confidence": None,
        "email_source_type": None,
        "errors": [],
        "current_step": None,
    }

    final_state = await research_graph.ainvoke(initial_state)

    if final_state.get("errors"):
        err_msg = "; ".join(final_state["errors"])
        raise ValueError(err_msg)

    social_models = [
        SocialProfile(**s) for s in final_state.get("social_profiles", [])
        if s.get("platform") in ALLOWED_PLATFORMS
    ]
    email_models = [EmailCandidate(**e) for e in final_state.get("email_candidates", [])]

    return RawCreatorResearchResult(
        video_url=final_state.get("video_url", ""),
        video_id=final_state.get("video_id", ""),
        video_title=final_state.get("video_title", ""),
        creator_name=final_state.get("creator_name", "Creator"),
        channel_name=final_state.get("channel_name", "Channel"),
        channel_handle=final_state.get("channel_handle"),
        channel_url=final_state.get("channel_url"),
        profile_image=final_state.get("profile_image"),
        subscriber_count=final_state.get("subscriber_count"),
        description=final_state.get("description"),
        channel_description=final_state.get("channel_description"),
        video_description=final_state.get("video_description"),
        channel_links=final_state.get("channel_links", []),
        published_at=final_state.get("published_at"),
        social_profiles=social_models,
        email_candidates=email_models,
        selected_email=final_state.get("selected_email"),
        email_source=final_state.get("email_source"),
        email_confidence=final_state.get("email_confidence"),
        email_source_type=final_state.get("email_source_type"),
        errors=final_state.get("errors", [])
    )


async def execute_creator_research_stream(youtube_url: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute LangGraph step-by-step and yield real-time progress events for SSE."""
    state: CreatorResearchState = {
        "video_url": youtube_url,
        "video_id": None,
        "channel_id": None,
        "creator_name": None,
        "channel_name": None,
        "channel_handle": None,
        "channel_url": None,
        "profile_image": None,
        "video_title": None,
        "subscriber_count": None,
        "description": None,
        "channel_description": None,
        "video_description": None,
        "channel_links": [],
        "published_at": None,
        "social_profiles": [],
        "email_candidates": [],
        "selected_email": None,
        "email_source": None,
        "email_confidence": None,
        "email_source_type": None,
        "errors": [],
        "current_step": None,
    }

    # Step 1: Validate URL
    yield {"step": 1, "name": "validate_url", "label": "Validating YouTube URL", "status": "running"}
    state.update(await validate_url_node(state))
    if state.get("errors"):
        yield {"step": 1, "name": "validate_url", "status": "error", "error": state["errors"][-1]}
        return
    yield {"step": 1, "name": "validate_url", "label": "YouTube URL validated", "status": "completed"}

    # Step 2: Fetch Metadata
    yield {"step": 2, "name": "fetch_metadata", "label": "Reading YouTube metadata & channel details", "status": "running"}
    state.update(await fetch_youtube_metadata_node(state))
    if state.get("errors"):
        yield {"step": 2, "name": "fetch_metadata", "status": "error", "error": state["errors"][-1]}
        return
    yield {"step": 2, "name": "fetch_metadata", "label": f"Found: {state.get('video_title', 'Video')}", "status": "completed"}

    # Step 3: Identify Creator
    yield {"step": 3, "name": "identify_creator", "label": "Matching channel identity & branding", "status": "running"}
    state.update(await identify_creator_node(state))
    yield {"step": 3, "name": "identify_creator", "label": f"Identified {state.get('creator_name')} ({state.get('channel_handle')})", "status": "completed"}

    # Step 4: Discover Socials
    yield {"step": 4, "name": "discover_socials", "label": "Scanning for public social profiles", "status": "running"}
    state.update(await discover_socials_node(state))
    social_count = len(state.get("social_profiles", []))
    yield {"step": 4, "name": "discover_socials", "label": f"Discovered {social_count} social profile(s)", "status": "completed"}

    # Step 5: Discover Emails
    yield {"step": 5, "name": "discover_emails", "label": "Searching for public business emails & contact links", "status": "running"}
    state.update(await discover_emails_node(state))
    email_count = len(state.get("email_candidates", []))
    yield {"step": 5, "name": "discover_emails", "label": f"Found {email_count} candidate email(s)", "status": "completed"}

    # Step 6: Classify & Finalize
    yield {"step": 6, "name": "classify_and_finalize", "label": "Classifying evidence with Mistral AI & finalizing profile", "status": "running"}
    state.update(await classify_and_finalize_node(state))

    social_models = [
        SocialProfile(**s) for s in state.get("social_profiles", [])
        if s.get("platform") in ALLOWED_PLATFORMS
    ]
    email_models = [EmailCandidate(**e) for e in state.get("email_candidates", [])]

    final_resp = RawCreatorResearchResult(
        video_url=state.get("video_url", ""),
        video_id=state.get("video_id", ""),
        video_title=state.get("video_title", ""),
        creator_name=state.get("creator_name", "Creator"),
        channel_name=state.get("channel_name", "Channel"),
        channel_handle=state.get("channel_handle"),
        channel_url=state.get("channel_url"),
        profile_image=state.get("profile_image"),
        subscriber_count=state.get("subscriber_count"),
        description=state.get("description"),
        channel_description=state.get("channel_description"),
        video_description=state.get("video_description"),
        channel_links=state.get("channel_links", []),
        published_at=state.get("published_at"),
        social_profiles=social_models,
        email_candidates=email_models,
        selected_email=state.get("selected_email"),
        email_source=state.get("email_source"),
        email_confidence=state.get("email_confidence"),
        email_source_type=state.get("email_source_type"),
        errors=state.get("errors", [])
    )

    yield {
        "step": 6,
        "name": "classify_and_finalize",
        "label": "Profile ready",
        "status": "completed",
        "data": final_resp.model_dump()
    }
