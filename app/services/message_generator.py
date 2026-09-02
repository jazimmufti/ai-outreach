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
    custom_notes: Optional[str] = None
) -> OutreachMessage:
    """Generate a high-converting, personalized outreach message via Gemini AI."""
    first_name = (creator_name or channel_name or "there").split(" ")[0]
    sender_display = sender_name or "Outreach Team"
    video_ref = f' ("{video_title}")' if video_title and len(video_title) > 3 else ""

    # Check if Gemini API key is configured
    if settings.GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            if channel == "instagram":
                system_prompt = (
                    "You are a friendly, professional influencer outreach specialist writing an Instagram Direct Message (DM). "
                    "Write a concise, engaging, and personalized DM to a creator. "
                    "Keep it under 90 words. Do NOT include a subject line. Do NOT include email sign-off formatting. "
                    "Sound genuine and conversational."
                )
                user_prompt = (
                    f"Write an Instagram DM to creator '{creator_name}' (Channel: '{channel_name}') "
                    f"referencing their content{video_ref}. "
                    f"Propose a potential partnership/collaboration opportunity. "
                    f"Additional context: {custom_notes or 'Exploring creative collaboration'}.\n"
                    f"Sender Name: {sender_display}\n\n"
                    f"Return a JSON object with: 'body' (string)."
                )
            else:
                system_prompt = (
                    "You are an expert partnership and sponsorship manager crafting a high-converting, personalized outreach email. "
                    "Write a compelling, professional, yet warm outreach email. "
                    "Structure: (1) Genuine compliment referencing their video, (2) Brief value proposition for collaboration, (3) Clear, low-friction call-to-action."
                )
                user_prompt = (
                    f"Write an outreach email to creator '{creator_name}' (Channel: '{channel_name}') "
                    f"referencing their video{video_ref}. "
                    f"Propose a collaboration/sponsorship discussion. "
                    f"Additional context: {custom_notes or 'Partnership opportunity'}.\n"
                    f"Sender Name: {sender_display}\n\n"
                    f"Return a JSON object with: 'subject' (string, compelling and under 60 chars) and 'body' (string)."
                )

            for model_name in ["gemini-3.6-flash", "gemini-flash-latest"]:
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.3,
                            response_mime_type="application/json"
                        )
                    )
                    if resp and resp.text:
                        parsed = json.loads(resp.text.strip())
                        if channel == "instagram":
                            return OutreachMessage(
                                recipient_name=creator_name,
                                subject=None,
                                body=parsed.get("body", "").strip(),
                                channel="instagram"
                            )
                        else:
                            return OutreachMessage(
                                recipient_name=creator_name,
                                subject=parsed.get("subject", f"Collaboration with {creator_name}"),
                                body=parsed.get("body", "").strip(),
                                channel=channel
                            )
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in Gemini message generation: {e}", exc_info=True)

    # Fallback template if Gemini is unavailable
    if channel == "instagram":
        body = (
            f"Hey {first_name}! Loved your recent content{video_ref}. "
            f"We're currently working with select creators in your space and would love to discuss a potential partnership. "
            f"Let me know if you're open to exploring a quick collaboration!"
        )
        return OutreachMessage(
            recipient_name=creator_name,
            subject=None,
            body=body,
            channel="instagram"
        )
    elif channel == "manual":
        subject = f"Collaboration Opportunity — {channel_name}"
        body = (
            f"Hi {first_name},\n\n"
            f"I came across your channel ({channel_name}) and really enjoyed your video{video_ref}.\n\n"
            f"We're looking to partner with outstanding creators like you for an upcoming campaign and think your audience would be a great fit.\n\n"
            f"Would you be open to a quick chat this week to explore collaboration possibilities?\n\n"
            f"Best regards,\n{sender_display}"
        )
        return OutreachMessage(
            recipient_name=creator_name,
            subject=subject,
            body=body,
            channel="manual"
        )
    else:
        subject = f"Collaboration Opportunity with {channel_name}"
        body = (
            f"Hi {first_name},\n\n"
            f"I recently watched your video{video_ref} and wanted to reach out directly to say how much I appreciated the insight and quality.\n\n"
            f"We are exploring partnerships with standout creators in your niche and believe there's strong alignment for a meaningful collaboration.\n\n"
            f"Do you have a few minutes later this week to discuss how we might work together?\n\n"
            f"Looking forward to hearing from you.\n\n"
            f"Best,\n{sender_display}"
        )
        return OutreachMessage(
            recipient_name=creator_name,
            subject=subject,
            body=body,
            channel="email"
        )
