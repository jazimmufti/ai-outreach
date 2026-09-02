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
    ManualEmailRequest,
    GenerateMessageRequest,
    SendEmailWorkflowRequest,
    SendEmailResponse
)
from app.services.session_manager import (
    create_session,
    get_session,
    save_session
)
from app.services.message_generator import generate_outreach_message
from app.services.gmail_service import get_gmail_status, send_test_email
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

        # Check discovered email
        if raw_result.selected_email:
            session.discovered_email = EmailCandidate(
                email=raw_result.selected_email,
                source=raw_result.email_source or "YouTube Channel Description",
                source_type=raw_result.email_source_type or "publicly_published",
                confidence=raw_result.email_confidence or "high",
                verification_status="Evidence verified"
            )
            session.stage = OutreachStage.CREATOR_FOUND
            has_reliable_email = True
        else:
            session.discovered_email = None
            session.stage = OutreachStage.NO_EMAIL_CHOICE
            has_reliable_email = False

        save_session(session)

        return CreatorDiscoveryResponse(
            session_id=session.session_id,
            stage=session.stage,
            creator=creator_profile,
            discovered_email=session.discovered_email,
            has_reliable_email=has_reliable_email,
            social_profiles=session.social_profiles,
            instagram_profile=session.instagram_profile,
            errors=raw_result.errors
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error in discovery workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/stream")
async def stream_discovery_endpoint(youtube_url: str = Query(..., description="YouTube video or channel URL")):
    """Step 1 Stream: Server-Sent Events for live step progress."""
    if not youtube_url:
        raise HTTPException(status_code=400, detail="Missing required 'youtube_url' parameter")

    session = create_session(youtube_url)

    async def event_generator():
        try:
            async for event in execute_creator_research_stream(youtube_url):
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

                    if raw.get("selected_email"):
                        session.discovered_email = EmailCandidate(
                            email=raw["selected_email"],
                            source=raw.get("email_source") or "YouTube Channel Description",
                            source_type=raw.get("email_source_type") or "publicly_published",
                            confidence=raw.get("email_confidence") or "high",
                            verification_status="Evidence verified"
                        )
                        session.stage = OutreachStage.CREATOR_FOUND
                        has_reliable_email = True
                    else:
                        session.discovered_email = None
                        session.stage = OutreachStage.NO_EMAIL_CHOICE
                        has_reliable_email = False

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
    session.stage = OutreachStage.MESSAGE_DRAFT
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
from datetime import datetime


class SimulateResponseRequest(BaseModel):
    session_id: str
    action: Literal["confirm", "reject"] = "confirm"


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


@router.get("/verify", response_class=HTMLResponse)
async def handle_creator_verification_response(
    session_id: str,
    action: str,
    token: Optional[str] = None
):
    """Public recipient endpoint: Handles Yes/No response from the sent email."""
    session = get_session(session_id)
    if not session:
        return HTMLResponse(
            content="""<!DOCTYPE html><html><body style="font-family:sans-serif;background:#FAF7F0;padding:40px;text-align:center;">
            <div style="max-width:400px;margin:0 auto;background:#fff;border:2px solid #111827;padding:30px;border-radius:4px;">
            <h2>Link Expired</h2><p>This verification link is no longer valid or has expired.</p>
            </div></body></html>""", 
            status_code=404
        )

    creator_name = session.creator.name if session.creator else "Creator"
    video_title = session.creator.video_title if session.creator else "the video"
    role = session.user_role or "Video editor"
    sub_count = (session.creator.subscriber_count or "").replace("subscribers", "").strip() if session.creator else ""
    audience_text = f"{creator_name}'s {sub_count} YouTube audience." if sub_count and sub_count != "Active Creator" else f"{creator_name}'s YouTube audience."

    if action == "confirm":
        session.creator_response = "confirmed"
        session.stage = OutreachStage.VERIFIED
        session.verified_at = datetime.utcnow().isoformat()
        save_session(session)

        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Confirmed — Arclent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
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
            max-width: 500px;
            width: 100%;
            background: #FFFFFF;
            border: 2px solid #111827;
            box-shadow: 6px 6px 0px #111827;
            border-radius: 4px;
            padding: 40px 32px;
            text-align: center;
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
            margin: 0 0 24px 0;
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
        <div class="icon-circle">✓</div>
        <h1>Collaboration Confirmed!</h1>
        <p>Thank you <strong>{creator_name}</strong>! You have verified this collaboration for <strong>{role}</strong> on <em>"{video_title}"</em>.</p>
        <div class="shield-box">
            <span>🛡</span>
            <span>Collaboration verified against {audience_text}</span>
        </div>
    </div>
</body>
</html>""")
    else:
        session.creator_response = "rejected"
        session.stage = OutreachStage.REJECTED
        save_session(session)

        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Response Recorded — Arclent</title>
    <style>
        body {{ background: #FAF7F0; font-family: -apple-system, sans-serif; color: #111827; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
        .card {{ max-width: 480px; width: 100%; background: #FFF; border: 2px solid #111827; box-shadow: 6px 6px 0px #111827; border-radius: 4px; padding: 36px 28px; text-align: center; }}
        .icon {{ width: 50px; height: 50px; border-radius: 50%; background: #EF4444; color: #fff; border: 2px solid #111827; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: bold; margin: 0 auto 16px auto; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✕</div>
        <h2>Response Recorded</h2>
        <p>You indicated you did not collaborate on this piece of content. Thank you for clarifying.</p>
    </div>
</body>
</html>""")


@router.post("/simulate-creator-response")
async def simulate_creator_response_endpoint(payload: SimulateResponseRequest):
    """Demo/Testing endpoint: Simulate the creator clicking 'Yes, I confirm' or 'No'."""
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if payload.action == "confirm":
        session.creator_response = "confirmed"
        session.stage = OutreachStage.VERIFIED
        session.verified_at = datetime.utcnow().isoformat()
    else:
        session.creator_response = "rejected"
        session.stage = OutreachStage.REJECTED

    save_session(session)
    return session


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
