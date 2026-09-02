"""Mistral AI reasoning and classification service."""

import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import EmailCandidate, SocialProfile

logger = logging.getLogger(__name__)

ALLOWED_PLATFORMS = {"Instagram", "X", "Discord", "Reddit", "Facebook"}


class EmailEvidenceClassification(BaseModel):
    """Schema for Mistral email classification output."""
    email: str
    source_type: str = Field(description="'publicly_published' or 'inferred'")
    confidence: str = Field(description="'high', 'medium', or 'low'")
    is_valid_contact: bool = Field(description="True if this email is a legitimate contact for the creator")
    reasoning: str = Field(description="Short reason for classification")


class ProfileVerificationResult(BaseModel):
    """Schema for Mistral profile & evidence reasoning."""
    selected_primary_email: Optional[str] = None
    classified_emails: List[EmailEvidenceClassification] = Field(default_factory=list)
    verified_socials: List[Dict[str, str]] = Field(default_factory=list)


async def call_mistral_chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    json_mode: bool = True
) -> Optional[str]:
    """Call Mistral AI chat completions with SDK or httpx fallback across resilient model list."""
    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        return None

    models_to_try = ["mistral-small-latest", "open-mistral-nemo", "mistral-large-latest"]

    # 1. Try mistralai SDK if available
    try:
        from mistralai import Mistral
        client = Mistral(api_key=api_key)

        for model in models_to_try:
            try:
                response_format = {"type": "json_object"} if json_mode else None
                kwargs = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                # Check if async completion is available on SDK
                if hasattr(client, "chat") and hasattr(client.chat, "complete_async"):
                    res = await client.chat.complete_async(**kwargs)
                elif hasattr(client, "chat") and hasattr(client.chat, "complete"):
                    res = client.chat.complete(**kwargs)
                else:
                    break

                if res and res.choices and len(res.choices) > 0:
                    content = res.choices[0].message.content
                    if content:
                        return content.strip()
            except Exception as model_err:
                logger.warning(f"Mistral SDK attempt failed for model {model}: {model_err}")
                continue
    except ImportError:
        logger.debug("mistralai SDK not installed or failed import, using direct HTTP API client.")
    except Exception as sdk_err:
        logger.warning(f"Mistral SDK error: {sdk_err}, falling back to httpx direct API.")

    # 2. Resilient Direct HTTP API fallback (standard Mistral API endpoint)
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        for model in models_to_try:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }

                res = await http_client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                else:
                    logger.warning(f"Mistral HTTP API returned status {res.status_code} for {model}: {res.text}")
            except Exception as http_err:
                logger.warning(f"Mistral HTTP API request failed for {model}: {http_err}")
                continue

    return None


async def classify_and_verify_with_mistral(
    creator_name: str,
    channel_name: str,
    video_title: str,
    description: str,
    raw_socials: List[SocialProfile],
    raw_emails: List[EmailCandidate],
    channel_description: Optional[str] = None,
    video_description: Optional[str] = None,
) -> Optional[ProfileVerificationResult]:
    """Use Mistral AI to reason over extracted evidence and classify email authenticity."""
    if not settings.MISTRAL_API_KEY:
        logger.info("MISTRAL_API_KEY not configured. Using deterministic fallback classification.")
        return None

    try:
        system_prompt = (
            "You are an expert AI research agent specialized in creator contact intelligence. "
            "Your task is to analyze candidate emails and social profiles discovered for a YouTube creator, "
            "and rigorously verify and classify them.\n\n"
            "STRICT RULES:\n"
            "1. NEVER invent or hallucinate an email. If none of the candidates are legitimate, return null for selected_primary_email.\n"
            "2. Distinguish between 'publicly_published' (explicitly stated on YouTube channel about/description or website) vs 'inferred' (guessed from domain).\n"
            "3. Reject sponsor/affiliate emails (e.g. support@expressvpn.com, contact@squarespace.com, discounts@brand.com).\n"
            "4. Assign email confidence:\n"
            "   - 'high': Publicly published specifically for business, management, booking, or creator contact.\n"
            "   - 'medium': Publicly found on creator's personal website or bio.\n"
            "   - 'low': Inferred, guessed, or ambiguous.\n"
            "5. SOCIAL PROFILES: ONLY verify and return profiles for these platforms: 'Instagram', 'X', 'LinkedIn', 'Facebook', 'Discord', 'Reddit', 'TikTok'. Do NOT include any other platforms.\n"
            "6. Return valid JSON matching the requested structure with keys: 'selected_primary_email', 'classified_emails', 'verified_socials'."
        )

        user_content = {
            "creator_name": creator_name,
            "channel_name": channel_name,
            "video_title": video_title,
            "channel_description_excerpt": (channel_description[:1500] if channel_description else "") or (description[:1500] if description else ""),
            "video_description_excerpt": video_description[:1500] if video_description else "",
            "candidate_emails": [e.model_dump() for e in raw_emails],
            "candidate_social_profiles": [s.model_dump() for s in raw_socials]
        }

        user_prompt = (
            f"Analyze this creator data and output JSON:\n```json\n{json.dumps(user_content, indent=2)}\n```\n\n"
            f"Return a JSON object with keys:\n"
            f"- 'selected_primary_email': string email address or null\n"
            f"- 'classified_emails': array of objects with keys ('email', 'source_type', 'confidence', 'is_valid_contact', 'reasoning')\n"
            f"- 'verified_socials': array of objects with keys ('platform', 'username', 'url', 'confidence')"
        )

        response_text = await call_mistral_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            json_mode=True
        )

        if not response_text:
            return None

        # Clean markdown fences if present
        content_text = response_text
        if content_text.startswith("```json"):
            content_text = content_text[7:]
        elif content_text.startswith("```"):
            content_text = content_text[3:]
        if content_text.endswith("```"):
            content_text = content_text[:-3]

        parsed = json.loads(content_text.strip())

        classified_list = []
        for item in parsed.get("classified_emails", []):
            classified_list.append(
                EmailEvidenceClassification(
                    email=item.get("email", ""),
                    source_type=item.get("source_type", "publicly_published"),
                    confidence=item.get("confidence", "medium"),
                    is_valid_contact=item.get("is_valid_contact", True),
                    reasoning=item.get("reasoning", "")
                )
            )

        # Filter verified_socials to strictly allowed platforms
        filtered_verified_socials = [
            s for s in parsed.get("verified_socials", [])
            if s.get("platform") in ALLOWED_PLATFORMS
        ]

        return ProfileVerificationResult(
            selected_primary_email=parsed.get("selected_primary_email"),
            classified_emails=classified_list,
            verified_socials=filtered_verified_socials
        )

    except Exception as e:
        logger.error(f"Mistral reasoning error: {e}", exc_info=True)
        return None


# Backward-compatible alias
classify_and_verify_with_gemini = classify_and_verify_with_mistral
