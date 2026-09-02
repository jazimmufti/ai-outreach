"""LangGraph orchestration graph for Creator Discovery & Intelligence."""

import logging
from typing import TypedDict, List, Optional, Dict, Any, AsyncGenerator
from langgraph.graph import StateGraph, START, END

from app.models.schemas import SocialProfile, EmailCandidate, RawCreatorResearchResult
from app.services.youtube_service import extract_video_id, get_youtube_metadata
from app.services.social_discovery import extract_social_profiles, extract_website_urls
from app.services.email_discovery import extract_emails_from_text, crawl_website_for_emails
from app.services.gemini_service import classify_and_verify_with_gemini

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
    """Node 1: Validate YouTube URL and extract video ID."""
    url = state.get("video_url", "").strip()
    video_id = extract_video_id(url)
    
    if not video_id:
        return {
            "current_step": "validate_url",
            "errors": state.get("errors", []) + [f"Invalid YouTube URL: {url}"]
        }
    
    return {
        "video_id": video_id,
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
            "video_title": data.get("video_title"),
            "creator_name": data.get("creator_name"),
            "channel_name": data.get("channel_name"),
            "channel_handle": data.get("channel_handle"),
            "channel_url": data.get("channel_url"),
            "profile_image": data.get("profile_image"),
            "subscriber_count": data.get("subscriber_count"),
            "description": data.get("description", ""),
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

    description = state.get("description", "")
    discovered_socials = extract_social_profiles(description, source_label="YouTube video description")
    
    # Strictly filter allowed platforms
    filtered_socials = [
        s.model_dump() for s in discovered_socials 
        if s.platform in ALLOWED_PLATFORMS
    ]
    
    return {
        "social_profiles": filtered_socials,
        "current_step": "discover_socials"
    }


async def discover_emails_node(state: CreatorResearchState) -> Dict[str, Any]:
    """Node 5: Discover candidate public emails from description and personal website."""
    if state.get("errors"):
        return state

    description = state.get("description", "")
    email_candidates: List[EmailCandidate] = []
    
    # 1. Search description
    desc_emails = extract_emails_from_text(description, source_label="YouTube video description")
    email_candidates.extend(desc_emails)

    # 2. Check if a personal website was found in description to crawl contact page
    website_urls = extract_website_urls(description)
    
    for site_url in website_urls[:2]:  # Limit to 2 websites max for speed
        if site_url:
            try:
                site_emails = await crawl_website_for_emails(site_url)
                email_candidates.extend(site_emails)
            except Exception as e:
                logger.debug(f"Website crawl error for {site_url}: {e}")

    # Deduplicate candidates by email address
    unique_candidates = []
    seen = set()
    for cand in email_candidates:
        if cand.email.lower() not in seen:
            seen.add(cand.email.lower())
            unique_candidates.append(cand.model_dump())

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
    
    raw_socials = [
        SocialProfile(**s) for s in state.get("social_profiles", [])
        if s.get("platform") in ALLOWED_PLATFORMS
    ]
    raw_emails = [EmailCandidate(**e) for e in state.get("email_candidates", [])]

    # Try Gemini reasoning
    gemini_result = await classify_and_verify_with_gemini(
        creator_name=creator_name,
        channel_name=channel_name,
        video_title=video_title,
        description=description,
        raw_socials=raw_socials,
        raw_emails=raw_emails
    )

    selected_email = None
    email_source = None
    email_confidence = None
    email_source_type = None

    if gemini_result and gemini_result.selected_primary_email:
        # Match with classified email
        selected_email = gemini_result.selected_primary_email
        for c in raw_emails:
            if c.email.lower() == selected_email.lower():
                email_source = c.source
                email_confidence = c.confidence
                email_source_type = c.source_type
                break
        if not email_source:
            email_source = "Verified via Gemini AI Analysis"
            email_confidence = "high"
            email_source_type = "publicly_published"

    # Deterministic fallback if Gemini is not configured or returned no primary email
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

    return {
        "selected_email": selected_email,
        "email_source": email_source,
        "email_confidence": email_confidence,
        "email_source_type": email_source_type,
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
    yield {"step": 6, "name": "classify_and_finalize", "label": "Classifying evidence with Gemini AI & finalizing profile", "status": "running"}
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
