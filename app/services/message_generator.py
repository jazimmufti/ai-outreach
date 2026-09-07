"""Message generation service for Creator Outreach."""

import json
import logging
from typing import Optional, Literal
from app.config import settings
from app.models.schemas import OutreachMessage

logger = logging.getLogger(__name__)


async def generate_outreach_message(
    creator_name: str,
    channel_name: str,
    video_title: Optional[str] = None,
    channel: Literal["email", "instagram", "manual"] = "email",
    sender_name: Optional[str] = None,
    user_role: Optional[str] = None,
    custom_notes: Optional[str] = None
) -> OutreachMessage:
    """Generate Arclent collaboration confirmation outreach message."""
    target_name = creator_name or channel_name or "Creator"
    role_text = (user_role or "Video editor").strip()
    
    clean_video_title = (video_title or "").strip()
    if clean_video_title:
        title_context = f' on "{clean_video_title}"'
        subject_title = f' for "{clean_video_title}"'
    else:
        title_context = " on your content"
        subject_title = ""

    if sender_name and sender_name.strip() and "someone on arclent" not in sender_name.lower():
        sender_label = sender_name.strip()
    elif channel == "instagram":
        sender_label = "your collaborator on Instagram"
    elif channel == "email" and sender_name:
        sender_label = sender_name.strip()
    else:
        sender_label = f"your collaborator ({role_text})"

    default_subject = f"Collaboration confirmation{subject_title}"
    default_body = f'Hi {target_name}, {sender_label} claims they worked as {role_text}{title_context}. Can you confirm this collaboration?'

    # If custom notes are provided or AI customization requested with Mistral AI
    if (settings.MISTRAL_API_KEY or settings.GEMINI_API_KEY) and custom_notes:
        try:
            from app.services.mistral_service import call_mistral_chat_completion

            system_prompt = (
                "You are an assistant for Arclent, a creator verification and collaboration platform. "
                "Your task is to write a concise collaboration verification inquiry to a YouTube creator. "
                f"Structure: 'Hi {{creator_name}}, {sender_label} claims they worked as {{role}} on \"{{video_title}}\". Can you confirm this collaboration?' "
                "Incorporate any specific custom notes naturally while keeping the message brief, clear, and professional."
            )
            user_prompt = (
                f"Creator Name: {target_name}\n"
                f"Channel Name: {channel_name}\n"
                f"Video Title: {clean_video_title}\n"
                f"Role: {role_text}\n"
                f"Channel: {channel}\n"
                f"Custom Notes: {custom_notes}\n\n"
                f"Return JSON object with 'subject' (string) and 'body' (string)."
            )

            resp_text = await call_mistral_chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                json_mode=True
            )

            if resp_text:
                if resp_text.startswith("```json"):
                    resp_text = resp_text[7:]
                elif resp_text.startswith("```"):
                    resp_text = resp_text[3:]
                if resp_text.endswith("```"):
                    resp_text = resp_text[:-3]

                parsed = json.loads(resp_text.strip())
                return OutreachMessage(
                    recipient_name=target_name,
                    subject=parsed.get("subject", default_subject) if channel != "instagram" else None,
                    body=parsed.get("body", default_body).strip(),
                    channel=channel
                )

        except Exception as e:
            logger.error(f"Error in Mistral message generation: {e}", exc_info=True)

    # Standard Arclent Collaboration Confirmation Template
    return OutreachMessage(
        recipient_name=target_name,
        subject=default_subject if channel != "instagram" else None,
        body=default_body,
        channel=channel
    )

