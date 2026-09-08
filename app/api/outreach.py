"""Step-by-step Creator Outreach Workflow API routes."""

import json
import logging
from typing import Optional, Literal
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, HTMLResponse

from app.models.schemas import (
    ResearchRequest,
    CreatorProfile,
    EmailCandidate,
    SocialProfile,
    OutreachStage,
    OutreachSession,
    CreatorDiscoveryResponse,
    ConfirmCreatorRequest,
    ConfirmEmailRequest,
    ConfirmInstagramRequest,
    ManualInstagramRequest,
    ManualEmailRequest,
    GenerateMessageRequest,
    SendEmailWorkflowRequest,
    SendEmailResponse,
    RecordSocialOutreachRequest,
    AutoVerificationResult
)
from datetime import datetime, timezone

from app.services.session_manager import (
    create_session,
    get_session,
    save_session
)
from app.services.message_generator import generate_outreach_message
from app.services.gmail_service import get_gmail_status, send_test_email
from app.services.linked_account import normalize_instagram_username
from app.services.auto_verification import verify_contribution_from_description
from app.workflows.creator_research_graph import execute_creator_research_stream, execute_creator_research

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outreach", tags=["outreach-workflow"])


@router.post("/discover", response_model=CreatorDiscoveryResponse)
async def discover_creator_endpoint(payload: ResearchRequest):
    """Step 1: Discover creator, public emails, and social profiles from a YouTube URL."""
    try:
        session = create_session(payload.youtube_url)
        session.user_role = payload.user_role or "Video editor"
        raw_result = await execute_creator_research(payload.youtube_url)

        creator_profile = CreatorProfile(
            name=raw_result.creator_name,
            channel_name=raw_result.channel_name,
            channel_handle=raw_result.channel_handle,
            channel_url=raw_result.channel_url,
            profile_image=raw_result.profile_image,
            subscriber_count=raw_result.subscriber_count,
            video_title=raw_result.video_title,
            video_url=raw_result.video_url,
            description=raw_result.description,
            channel_description=raw_result.channel_description,
            video_description=raw_result.video_description,
            channel_links=raw_result.channel_links
        )

        session.creator = creator_profile
        session.social_profiles = raw_result.social_profiles

        # Locate Instagram profile if available
        for s in raw_result.social_profiles:
            if s.platform == "Instagram":
                session.instagram_profile = s
                break

        # Step 0: Automatic Contribution Verification via YouTube Video Description
        # Checks whether creator mentions match the Arclent linked Instagram account
        desc_parts = [
            raw_result.video_description or "",
            raw_result.description or "",
            raw_result.channel_description or ""
        ]
        desc_to_check = "\n".join(p for p in desc_parts if p.strip())
        auto_verify_result = verify_contribution_from_description(
            desc_to_check,
            linked_account=payload.linked_instagram_account
        )
        session.auto_verification = auto_verify_result

        # Check discovered email
        if raw_result.selected_email:
            session.discovered_email = EmailCandidate(
                email=raw_result.selected_email,
                source=raw_result.email_source or "YouTube Channel Description",
                source_type=raw_result.email_source_type or "publicly_published",
                confidence=raw_result.email_confidence or "high",
                verification_status="Evidence verified"
            )
            has_reliable_email = True
        else:
            session.discovered_email = None
            has_reliable_email = False

        if auto_verify_result.verified:
            session.stage = OutreachStage.AUTO_VERIFIED
            session.creator_response = "confirmed"
            if not session.verified_at:
                session.verified_at = datetime.now(timezone.utc).isoformat()
        else:
            session.stage = OutreachStage.CREATOR_FOUND if has_reliable_email else OutreachStage.NO_EMAIL_CHOICE

        save_session(session)

        return CreatorDiscoveryResponse(
            session_id=session.session_id,
            stage=session.stage,
            creator=creator_profile,
            discovered_email=session.discovered_email,
            has_reliable_email=has_reliable_email,
            social_profiles=session.social_profiles,
            instagram_profile=session.instagram_profile,
            auto_verification=session.auto_verification,
            errors=raw_result.errors
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in discovery workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/stream")
async def stream_discovery_endpoint(
    youtube_url: str = Query(..., description="YouTube video or channel URL"),
    user_role: Optional[str] = Query(None, description="Role on the piece of content"),
    linked_account: Optional[str] = Query(None, description="User's linked Instagram handle")
):
    """Step 1 Stream: Server-Sent Events for live step progress."""
    if not youtube_url:
        raise HTTPException(status_code=400, detail="Missing required 'youtube_url' parameter")

    session = create_session(youtube_url)
    session.user_role = user_role or "Video editor"

    async def event_generator():
        try:
            async for event in execute_creator_research_stream(youtube_url):
                event["session_id"] = session.session_id
                # When finalized, save to session
                if event.get("step") == 6 and event.get("status") == "completed" and event.get("data"):
                    raw = event["data"]
                    creator_profile = CreatorProfile(
                        name=raw.get("creator_name", "Creator"),
                        channel_name=raw.get("channel_name", "Channel"),
                        channel_handle=raw.get("channel_handle"),
                        channel_url=raw.get("channel_url"),
                        profile_image=raw.get("profile_image"),
                        subscriber_count=raw.get("subscriber_count"),
                        video_title=raw.get("video_title"),
                        video_url=raw.get("video_url"),
                        description=raw.get("description"),
                        channel_description=raw.get("channel_description"),
                        video_description=raw.get("video_description"),
                        channel_links=raw.get("channel_links", [])
                    )
                    session.creator = creator_profile
                    session.social_profiles = [SocialProfile(**s) for s in raw.get("social_profiles", [])]

                    for s in session.social_profiles:
                        if s.platform == "Instagram":
                            session.instagram_profile = s
                            break

                    # Step 0: Automatic Contribution Verification via YouTube Video Description
                    desc_parts = [
                        raw.get("video_description") or "",
                        raw.get("description") or "",
                        raw.get("channel_description") or ""
                    ]
                    desc_to_check = "\n".join(p for p in desc_parts if p.strip())
                    auto_verify_result = verify_contribution_from_description(
                        desc_to_check,
                        linked_account=linked_account
                    )
                    session.auto_verification = auto_verify_result

                    if raw.get("selected_email"):
                        session.discovered_email = EmailCandidate(
                            email=raw["selected_email"],
                            source=raw.get("email_source") or "YouTube Channel Description",
                            source_type=raw.get("email_source_type") or "publicly_published",
                            confidence=raw.get("email_confidence") or "high",
                            verification_status="Evidence verified"
                        )
                        has_reliable_email = True
                    else:
                        session.discovered_email = None
                        has_reliable_email = False

                    if auto_verify_result.verified:
                        session.stage = OutreachStage.AUTO_VERIFIED
                        session.creator_response = "confirmed"
                        if not session.verified_at:
                            session.verified_at = datetime.now(timezone.utc).isoformat()
                    else:
                        session.stage = OutreachStage.CREATOR_FOUND if has_reliable_email else OutreachStage.NO_EMAIL_CHOICE

                    save_session(session)

                    # Build complete CreatorDiscoveryResponse payload
                    final_resp_payload = CreatorDiscoveryResponse(
                        session_id=session.session_id,
                        stage=session.stage,
                        creator=creator_profile,
                        discovered_email=session.discovered_email,
                        has_reliable_email=has_reliable_email,
                        social_profiles=session.social_profiles,
                        instagram_profile=session.instagram_profile,
                        auto_verification=session.auto_verification,
                        errors=raw.get("errors", [])
                    )
                    event["data"] = final_resp_payload.model_dump()

                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/confirm-email")
async def confirm_email_endpoint(payload: ConfirmEmailRequest):
    """Step 1: Confirm whether the discovered email is the correct recipient."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    if payload.user_role:
        session.user_role = payload.user_role

    session.email_confirmed = payload.email_confirmed

    if payload.email_confirmed and session.discovered_email:
        session.final_email = session.discovered_email.email
        session.email_source = session.discovered_email.source
        session.email_confidence = session.discovered_email.confidence
        session.email_verification_status = "verified_evidence"
    else:
        # User indicated "No, not them" or email rejected
        session.email_confirmed = False
        session.final_email = None

    session.stage = OutreachStage.VERIFY_INSTAGRAM
    save_session(session)
    return session


@router.post("/confirm-instagram")
async def confirm_instagram_endpoint(payload: ConfirmInstagramRequest):
    """Step 2: Confirm whether the discovered Instagram profile is correct."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    if payload.user_role:
        session.user_role = payload.user_role

    session.instagram_confirmed = payload.instagram_confirmed

    if payload.instagram_confirmed and session.instagram_profile:
        session.final_instagram_handle = session.instagram_profile.username
        session.final_instagram_url = session.instagram_profile.url
    else:
        session.instagram_confirmed = False
        session.final_instagram_handle = None
        session.final_instagram_url = None

    session.stage = OutreachStage.OUTREACH_HUB
    save_session(session)
    return session


@router.post("/manual-instagram")
async def submit_manual_instagram_endpoint(payload: ManualInstagramRequest):
    """Step 2 Fallback: Set user-provided Instagram handle."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    if payload.user_role:
        session.user_role = payload.user_role

    clean_handle = payload.handle.lstrip("@").strip()
    session.instagram_confirmed = True
    session.final_instagram_handle = f"@{clean_handle}"
    session.final_instagram_url = f"https://instagram.com/{clean_handle}"
    
    # Create or update instagram profile entry
    session.instagram_profile = SocialProfile(
        platform="Instagram",
        username=f"@{clean_handle}",
        url=f"https://instagram.com/{clean_handle}",
        source="User manually entered",
        confidence="high"
    )
    session.stage = OutreachStage.OUTREACH_HUB
    save_session(session)
    return session


@router.post("/confirm")
async def confirm_creator_endpoint(payload: ConfirmCreatorRequest):
    """Step 2 Decision: Confirm whether the discovered creator is the correct target."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found. Please restart from Step 1.")

    if not session.creator:
        raise HTTPException(status_code=400, detail="Invalid session state: No creator identified yet.")

    if payload.user_role:
        session.user_role = payload.user_role

    session.creator_confirmed = payload.creator_confirmed

    if payload.creator_confirmed:
        # YES PATH
        if session.discovered_email:
            session.final_email = session.discovered_email.email
            session.email_source = session.discovered_email.source
            session.email_confidence = session.discovered_email.confidence
            session.email_verification_status = "verified_evidence"
            session.stage = OutreachStage.MESSAGE_DRAFT
            session.selected_channel = "email"

            # Pre-generate outreach email message
            gmail_stat = get_gmail_status()
            sender_name = gmail_stat.get("email")
            session.message = await generate_outreach_message(
                creator_name=session.creator.name,
                channel_name=session.creator.channel_name,
                video_title=session.creator.video_title,
                channel="email",
                sender_name=sender_name,
                user_role=session.user_role
            )
        else:
            session.stage = OutreachStage.NO_EMAIL_CHOICE

    else:
        # NO PATH: "No, that's not the right creator"
        # Strictly invalidate any discovered email
        session.discovered_email = None
        session.final_email = None
        session.email_source = None
        session.stage = OutreachStage.MANUAL_EMAIL_INPUT

    save_session(session)
    return session


@router.post("/manual-email")
async def submit_manual_email_endpoint(payload: ManualEmailRequest):
    """Step 2 Fallback: Set verified user-provided contact email."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found. Please restart.")

    if payload.user_role:
        session.user_role = payload.user_role

    session.final_email = payload.email
    session.email_source = "User manually entered"
    session.email_confidence = "high"
    session.email_verification_status = "user_provided"
    session.email_confirmed = True
    session.stage = OutreachStage.VERIFY_INSTAGRAM
    session.selected_channel = "email"

    # Pre-generate email message
    gmail_stat = get_gmail_status()
    sender_name = gmail_stat.get("email")
    session.message = await generate_outreach_message(
        creator_name=session.creator.name if session.creator else "Creator",
        channel_name=session.creator.channel_name if session.creator else "Creator",
        video_title=session.creator.video_title if session.creator else None,
        channel="email",
        sender_name=sender_name,
        user_role=session.user_role
    )

    save_session(session)
    return session


@router.post("/generate-message")
async def generate_message_endpoint(payload: GenerateMessageRequest):
    """Step 3 Message Generation: Generate or regenerate customized outreach message."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    if not session.creator:
        raise HTTPException(status_code=400, detail="Cannot generate message without a creator.")

    if payload.user_role:
        session.user_role = payload.user_role

    gmail_stat = get_gmail_status()
    sender_name = gmail_stat.get("email")

    msg = await generate_outreach_message(
        creator_name=session.creator.name,
        channel_name=session.creator.channel_name,
        video_title=session.creator.video_title,
        channel=payload.channel,
        sender_name=sender_name,
        user_role=session.user_role,
        custom_notes=payload.custom_notes
    )

    session.message = msg
    session.selected_channel = payload.channel

    if payload.channel == "instagram":
        session.stage = OutreachStage.INSTAGRAM_READY
    elif payload.channel == "manual":
        session.stage = OutreachStage.MANUAL_MESSAGE_READY
    else:
        session.stage = OutreachStage.MESSAGE_DRAFT

    save_session(session)
    return {
        "session_id": session.session_id,
        "stage": session.stage,
        "message": msg,
        "final_email": session.final_email,
        "instagram_profile": session.instagram_profile
    }


import secrets
from datetime import datetime, timezone


@router.post("/send-email", response_model=SendEmailResponse)
async def send_email_workflow_endpoint(payload: SendEmailWorkflowRequest, request: Request):
    """Step 4 Send: Dispatch real outreach email via connected Gmail account with Yes/No verification links."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    recipient = (payload.recipient or session.final_email or "").strip()
    if not recipient:
        raise HTTPException(status_code=400, detail="No recipient email address specified.")

    gmail_stat = get_gmail_status()
    if not gmail_stat.get("connected"):
        raise HTTPException(
            status_code=400, 
            detail="Gmail account is not connected. Please connect your Gmail account via OAuth first."
        )

    # Generate cryptographically secure verification token
    verification_token = secrets.token_urlsafe(16)
    session.verification_token = verification_token

    # Build recipient confirmation and rejection URLs
    base_url = str(request.base_url).rstrip("/")
    confirm_url = f"{base_url}/api/outreach/verify?session_id={session.session_id}&action=confirm&token={verification_token}"
    reject_url = f"{base_url}/api/outreach/verify?session_id={session.session_id}&action=reject&token={verification_token}"

    try:
        result = send_test_email(
            recipient=recipient,
            subject=payload.subject,
            body=payload.body,
            confirm_url=confirm_url,
            reject_url=reject_url
        )

        session.stage = OutreachStage.SENT
        session.creator_response = "pending"
        session.selected_channel = "email"
        session.sender_identity = "Someone on Arclent"
        save_session(session)

        return SendEmailResponse(
            success=True,
            message="Outreach email sent successfully via Gmail API",
            recipient=result["recipient"],
            sender=result.get("sender"),
            message_id=result.get("message_id"),
            timestamp=result.get("timestamp")
        )
    except Exception as e:
        logger.error(f"Failed to send email via workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def format_sender_display(session: OutreachSession) -> str:
    """Format sender identity: 'Someone on Arclent' for email/fallback, or '{username} on Arclent' for social/Instagram."""
    # 1. If a specific user sender_handle was provided (e.g. from Instagram / social outreach)
    if session.sender_handle and session.sender_handle.strip():
        handle = session.sender_handle.strip().lstrip("@")
        if handle:
            return f"{handle} on Arclent"

    # 2. If sender_identity was set and formatted
    if session.sender_identity and session.sender_identity.strip():
        val = session.sender_identity.strip()
        # Ensure company email address is never displayed as sender identity
        if "@" in val and "." in val and " " not in val:
            return "Someone on Arclent"
        if val != "Someone on Arclent" and " on Arclent" not in val and "@" not in val:
            return f"{val} on Arclent"
        return val

    # 3. Default for email and unauthenticated outreach
    return "Someone on Arclent"


@router.post("/record-social-outreach")
async def record_social_outreach_endpoint(payload: RecordSocialOutreachRequest):
    """Step 4 Send (Social): Record that outreach was dispatched via Instagram or other social platform."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    platform_str = payload.platform or "Instagram"
    session.selected_channel = platform_str.lower()
    if payload.handle:
        session.final_instagram_handle = payload.handle

    if payload.sender_handle and payload.sender_handle.strip():
        raw_h = payload.sender_handle.strip().lstrip("@")
        session.sender_handle = raw_h
        session.sender_identity = f"{raw_h} on Arclent"
    elif payload.sender_identity and payload.sender_identity.strip() and "@" not in payload.sender_identity:
        clean_id = payload.sender_identity.strip()
        if clean_id.endswith(" on Arclent"):
            session.sender_identity = clean_id
            session.sender_handle = clean_id.replace(" on Arclent", "").strip().lstrip("@")
        else:
            session.sender_identity = f"{clean_id} on Arclent"
            session.sender_handle = clean_id.lstrip("@")
    elif not session.sender_handle:
        session.sender_identity = "Someone on Arclent"

    session.stage = OutreachStage.SENT
    session.creator_response = "pending"
    save_session(session)
    return {
        "success": True,
        "session_id": session.session_id,
        "stage": session.stage,
        "selected_channel": session.selected_channel,
        "sender_handle": session.sender_handle,
        "sender_identity": session.sender_identity,
        "creator_response": session.creator_response
    }


@router.get("/verify", response_class=HTMLResponse)
async def handle_creator_verification_response(
    session_id: str,
    action: Optional[str] = None,
    token: Optional[str] = None
):
    """Public recipient endpoint: Handles Yes/No response or interactive review page."""
    session = get_session(session_id)
    if not session:
        return HTMLResponse(
            content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Link Expired — Arclent</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
    <style>
        body { background-color: #FAF7F0; font-family: 'Plus Jakarta Sans', sans-serif; color: #111827; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }
        .card { max-width: 440px; width: 100%; background: #FFFFFF; border: 2px solid #111827; box-shadow: 6px 6px 0px #111827; border-radius: 4px; padding: 36px 28px; text-align: center; }
        h2 { font-family: 'Space Grotesk', sans-serif; font-size: 22px; margin: 0 0 10px; }
        p { font-size: 14.5px; color: #4B5563; line-height: 1.5; margin: 0; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Verification Link Expired</h2>
        <p>This verification link is no longer valid or the collaboration session was not found.</p>
    </div>
</body>
</html>""", 
            status_code=404
        )

    creator_name = session.creator.name if session.creator else "Creator"
    channel_name = session.creator.channel_name if session.creator else creator_name
    video_title = session.creator.video_title if session.creator else "the video"
    role = session.user_role or "Video editor"
    sub_count = (session.creator.subscriber_count or "").replace("subscribers", "").strip() if session.creator else ""
    audience_text = f"{creator_name}'s {sub_count} YouTube audience." if sub_count and sub_count != "Active Creator" else f"{creator_name}'s YouTube audience."
    sender_display = format_sender_display(session)

    # Check whether session was already confirmed or rejected before this request
    was_already_confirmed = (session.creator_response == "confirmed" or session.stage == OutreachStage.VERIFIED)
    was_already_rejected = (session.creator_response == "rejected" or session.stage == OutreachStage.REJECTED)

    # --------------------------------------------------------------------------
    # CASE 1: Session is already Confirmed (or action=confirm)
    # --------------------------------------------------------------------------
    if was_already_confirmed or action == "confirm":
        is_already = was_already_confirmed
        session.creator_response = "confirmed"
        session.stage = OutreachStage.VERIFIED
        if not session.verified_at:
            session.verified_at = datetime.now(timezone.utc).isoformat()
        save_session(session)

        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Confirmed — Arclent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@700;800&family=JetBrains+Mono:wght@600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background-color: #FAF7F0;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }}
        .card {{
            max-width: 520px;
            width: 100%;
            background: #FFFFFF;
            border: 2px solid #111827;
            box-shadow: 6px 6px 0px #111827;
            border-radius: 4px;
            padding: 40px 32px;
            text-align: center;
        }}
        .brand-row {{
            margin-bottom: 24px;
            padding-bottom: 14px;
            border-bottom: 1.5px solid #E5E7EB;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .brand-text {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border: 1.5px solid #111827;
            background: #00D26A;
            color: #000;
            border-radius: 2px;
        }}
        .icon-circle {{
            width: 54px;
            height: 54px;
            border-radius: 50%;
            background: #00D26A;
            border: 2px solid #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            font-weight: 800;
            margin: 0 auto 20px auto;
        }}
        h1 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 25px;
            font-weight: 800;
            margin: 0 0 10px 0;
            letter-spacing: -0.02em;
        }}
        p {{
            font-size: 15px;
            color: #4B5563;
            line-height: 1.55;
            margin: 0 0 20px 0;
        }}
        .collab-meta-box {{
            background: #FAF8F2;
            border: 1.5px solid #111827;
            border-radius: 3px;
            padding: 14px 18px;
            margin-bottom: 22px;
            text-align: left;
        }}
        .meta-row {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            padding: 7px 0;
            border-bottom: 1px dashed #D1D5DB;
            font-size: 13px;
        }}
        .meta-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .meta-row:first-child {{
            padding-top: 0;
        }}
        .meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            color: #6B7280;
            flex-shrink: 0;
            margin-right: 10px;
        }}
        .meta-value {{
            font-weight: 700;
            color: #111827;
            text-align: right;
            word-break: break-word;
        }}
        .shield-box {{
            background: #E8FDF0;
            border: 1.5px solid #00D26A;
            border-radius: 2px;
            padding: 14px 18px;
            font-size: 13.5px;
            color: #065F46;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-row">
            <span class="brand-text">Arclent</span>
            <span class="status-badge">✓ VERIFIED</span>
        </div>
        <div class="icon-circle">✓</div>
        <h1>{"You've already confirmed this collaboration" if is_already else "Collaboration Confirmed!"}</h1>
        <p>Thank you <strong>{creator_name}</strong>! You have verified this collaboration for <strong>{role}</strong> on <em>"{video_title}"</em>.</p>
        
        <div class="collab-meta-box">
            <div class="meta-row">
                <span class="meta-label">CREATOR / CHANNEL</span>
                <span class="meta-value">{creator_name}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">CLAIMED ROLE</span>
                <span class="meta-value">{role}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">PROJECT CONTENT</span>
                <span class="meta-value">"{video_title}"</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">REQUESTED BY</span>
                <span class="meta-value">{sender_display}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">STATUS</span>
                <span class="meta-value" style="color: #065F46;">✓ Confirmed & Verified</span>
            </div>
        </div>

        <div class="shield-box">
            <span>🛡</span>
            <span>Collaboration verified against {audience_text}</span>
        </div>
    </div>
</body>
</html>""")

    # --------------------------------------------------------------------------
    # CASE 2: Session is already Rejected (or action=reject)
    # --------------------------------------------------------------------------
    if was_already_rejected or action == "reject":
        is_already = was_already_rejected
        session.creator_response = "rejected"
        session.stage = OutreachStage.REJECTED
        if not session.verified_at:
            session.verified_at = datetime.now(timezone.utc).isoformat()
        save_session(session)

        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Declined — Arclent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@700;800&family=JetBrains+Mono:wght@600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            background: #FAF7F0;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }}
        .card {{
            max-width: 480px;
            width: 100%;
            background: #FFFFFF;
            border: 2px solid #111827;
            box-shadow: 6px 6px 0px #111827;
            border-radius: 4px;
            padding: 40px 32px;
            text-align: center;
        }}
        .brand-row {{
            margin-bottom: 24px;
            padding-bottom: 14px;
            border-bottom: 1.5px solid #E5E7EB;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .brand-text {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 800;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border: 1.5px solid #111827;
            background: #FEE2E2;
            color: #991B1B;
            border-radius: 2px;
        }}
        .icon-circle {{
            width: 54px;
            height: 54px;
            border-radius: 50%;
            background: #FEE2E2;
            color: #DC2626;
            border: 2px solid #DC2626;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            font-weight: 800;
            margin: 0 auto 20px auto;
        }}
        h1 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 24px;
            font-weight: 800;
            margin: 0 0 10px 0;
            color: #991B1B;
            letter-spacing: -0.02em;
        }}
        p {{
            font-size: 15px;
            color: #4B5563;
            line-height: 1.55;
            margin: 0 0 20px 0;
        }}
        .collab-meta-box {{
            background: #FAF8F2;
            border: 1.5px solid #111827;
            border-radius: 3px;
            padding: 14px 18px;
            margin-bottom: 22px;
            text-align: left;
        }}
        .meta-row {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            padding: 7px 0;
            border-bottom: 1px dashed #D1D5DB;
            font-size: 13px;
        }}
        .meta-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .meta-row:first-child {{
            padding-top: 0;
        }}
        .meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 700;
            color: #6B7280;
            flex-shrink: 0;
            margin-right: 10px;
        }}
        .meta-value {{
            font-weight: 700;
            color: #111827;
            text-align: right;
            word-break: break-word;
        }}
        .declined-box {{
            background: #FEF2F2;
            border: 1.5px solid #FCA5A5;
            border-radius: 2px;
            padding: 14px 18px;
            font-size: 13.5px;
            color: #991B1B;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-row">
            <span class="brand-text">Arclent</span>
            <span class="status-badge">✕ DECLINED</span>
        </div>
        <div class="icon-circle">✕</div>
        <h1>{"You've already rejected this collaboration" if is_already else "Response Recorded"}</h1>
        <p>Thank you <strong>{creator_name}</strong>. Your response has been recorded that you did not collaborate on <em>"{video_title}"</em>.</p>
        
        <div class="collab-meta-box">
            <div class="meta-row">
                <span class="meta-label">CREATOR / CHANNEL</span>
                <span class="meta-value">{creator_name}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">CLAIMED ROLE</span>
                <span class="meta-value">{role}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">PROJECT CONTENT</span>
                <span class="meta-value">"{video_title}"</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">REQUESTED BY</span>
                <span class="meta-value">{sender_display}</span>
            </div>
        </div>

        <div class="declined-box">
            <span>✕</span>
            <span>Collaboration declined and marked unverified</span>
        </div>
    </div>
</body>
</html>""")

    # --------------------------------------------------------------------------
    # CASE 3: First-time Interactive Review & Confirmation Page (Yes / No)
    # --------------------------------------------------------------------------
    token_param = f"&token={token}" if token else ""
    confirm_href = f"/verify?session_id={session.session_id}&action=confirm{token_param}"
    reject_href = f"/verify?session_id={session.session_id}&action=reject{token_param}"

    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Confirmation — Arclent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: #FAF7F0;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            color: #111827;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px 16px;
        }}
        .card {{
            max-width: 540px;
            width: 100%;
            background: #FFFFFF;
            border: 2px solid #111827;
            box-shadow: 6px 6px 0px #111827;
            border-radius: 4px;
            padding: 36px 30px;
            text-align: center;
        }}
        .brand-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 14px;
            margin-bottom: 22px;
            border-bottom: 1.5px solid #E5E7EB;
        }}
        .brand-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -0.02em;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            font-weight: 700;
            padding: 4px 10px;
            border: 1.5px solid #111827;
            background: #FBF0D9;
            border-radius: 2px;
        }}
        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #F59E0B;
        }}
        .main-heading {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 24px;
            font-weight: 800;
            line-height: 1.3;
            letter-spacing: -0.02em;
            margin-bottom: 10px;
        }}
        .body-desc {{
            font-size: 15px;
            color: #4B5563;
            line-height: 1.55;
            margin-bottom: 22px;
        }}
        .collab-meta-box {{
            background: #FAF8F2;
            border: 1.5px solid #111827;
            border-radius: 3px;
            padding: 16px 20px;
            margin-bottom: 24px;
            text-align: left;
        }}
        .meta-row {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px dashed #D1D5DB;
            font-size: 13.5px;
        }}
        .meta-row:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .meta-row:first-child {{
            padding-top: 0;
        }}
        .meta-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11.5px;
            font-weight: 700;
            color: #6B7280;
            flex-shrink: 0;
            margin-right: 12px;
        }}
        .meta-value {{
            font-weight: 700;
            color: #111827;
            text-align: right;
            word-break: break-word;
        }}
        .btn-stack {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 20px;
            margin-bottom: 22px;
        }}
        .btn-confirm {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #00D26A;
            color: #000000;
            text-decoration: none;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 15px;
            font-weight: 700;
            padding: 14px 24px;
            border: 2px solid #111827;
            border-radius: 2px;
            box-shadow: 3px 3px 0px #111827;
            transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.15s ease;
        }}
        .btn-confirm:hover {{
            background: #00B359;
            transform: translate(-1px, -1px);
            box-shadow: 4px 4px 0px #111827;
        }}
        .btn-confirm:active {{
            transform: translate(2px, 2px);
            box-shadow: 1px 1px 0px #111827;
        }}
        .btn-reject {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #FFFFFF;
            color: #111827;
            text-decoration: none;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 14.5px;
            font-weight: 700;
            padding: 12px 20px;
            border: 2px solid #111827;
            border-radius: 2px;
            box-shadow: 3px 3px 0px #111827;
            transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.15s ease;
        }}
        .btn-reject:hover {{
            background: #FEF2F2;
            color: #DC2626;
            border-color: #DC2626;
            transform: translate(-1px, -1px);
            box-shadow: 4px 4px 0px #DC2626;
        }}
        .btn-reject:active {{
            transform: translate(2px, 2px);
            box-shadow: 1px 1px 0px #111827;
        }}
        .footer-note {{
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: #6B7280;
            border-top: 1px solid #E5E7EB;
            padding-top: 14px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-header">
            <span class="brand-title">Arclent</span>
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>COLLABORATION VERIFICATION</span>
            </div>
        </div>

        <h1 class="main-heading">Can you confirm this collaboration?</h1>
        <p class="body-desc">
            <strong>{sender_display}</strong> claims they worked as <strong>{role}</strong> on <em>"{video_title}"</em>.
        </p>

        <div class="collab-meta-box">
            <div class="meta-row">
                <span class="meta-label">CREATOR / CHANNEL</span>
                <span class="meta-value">{creator_name}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">CLAIMED ROLE</span>
                <span class="meta-value">{role}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">PROJECT CONTENT</span>
                <span class="meta-value">"{video_title}"</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">REQUESTED BY</span>
                <span class="meta-value">{sender_display}</span>
            </div>
        </div>

        <div class="btn-stack">
            <a href="{confirm_href}" class="btn-confirm">
                <span>✓ Yes, I confirm this collaboration</span>
            </a>
            <a href="{reject_href}" class="btn-reject">
                <span>✕ No, I do not confirm</span>
            </a>
        </div>

        <div class="footer-note">
            Sent securely via Arclent • Creator Collaboration & Credentials Verification
        </div>
    </div>
</body>
</html>""")





class VerifyLinkedAccountRequest(BaseModel):
    session_id: str
    instagram_account: str


@router.post("/verify-linked-account")
async def verify_linked_account_endpoint(payload: VerifyLinkedAccountRequest):
    """Dynamically verify an unlinked user when they connect their Instagram account."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Outreach session expired or not found.")

    clean_handle = normalize_instagram_username(payload.instagram_account)
    if not clean_handle:
        raise HTTPException(status_code=400, detail="Invalid Instagram handle provided.")

    extracted = []
    if session.auto_verification and session.auto_verification.extracted_accounts:
        extracted = [h.lower().lstrip("@") for h in session.auto_verification.extracted_accounts]

    if clean_handle.lower() in extracted:
        auto_result = AutoVerificationResult(
            verified=True,
            status="auto_verified",
            method="youtube_description_instagram_match",
            matched_account=clean_handle,
            linked_account=clean_handle,
            extracted_accounts=extracted,
            reason=f"Connected Instagram account @{clean_handle} matches contributor credits published in the video description."
        )
        session.auto_verification = auto_result
        session.stage = OutreachStage.AUTO_VERIFIED
        session.creator_response = "confirmed"
        session.verified_at = datetime.now(timezone.utc).isoformat()
        save_session(session)
        return {
            "verified": True,
            "matched_account": clean_handle,
            "session_id": session.session_id,
            "auto_verification": auto_result
        }

    return {
        "verified": False,
        "matched_account": None,
        "session_id": session.session_id,
        "extracted_accounts": extracted,
        "message": f"Connected @{clean_handle}, but credits in description were for: {', '.join(f'@{a}' for a in extracted)}"
    }


@router.get("/session-status")
async def get_session_status_query(session_id: str):
    """Poll session status for realtime verification updates."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.get("/session/{session_id}")
async def get_session_status_endpoint(session_id: str):
    """Retrieve full session object."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session
