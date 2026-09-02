"""Step-by-step Creator Outreach Workflow API routes."""

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

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
            description=raw_result.description
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
                source=raw_result.email_source or "YouTube video description",
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
                        description=raw.get("description")
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
                            source=raw.get("email_source") or "YouTube description",
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
                sender_name=sender_name
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
        sender_name=sender_name
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

    gmail_stat = get_gmail_status()
    sender_name = gmail_stat.get("email")

    msg = await generate_outreach_message(
        creator_name=session.creator.name,
        channel_name=session.creator.channel_name,
        video_title=session.creator.video_title,
        channel=payload.channel,
        sender_name=sender_name,
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


@router.post("/send-email", response_model=SendEmailResponse)
async def send_email_workflow_endpoint(payload: SendEmailWorkflowRequest):
    """Step 4 Send: Dispatch real outreach email via connected Gmail account."""
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

    try:
        result = send_test_email(
            recipient=recipient,
            subject=payload.subject,
            body=payload.body
        )

        session.stage = OutreachStage.SENT
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


@router.get("/session/{session_id}")
async def get_session_status_endpoint(session_id: str):
    """Retrieve full session object."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session
