"""Gemini reasoning and classification service."""

import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import EmailCandidate, SocialProfile

logger = logging.getLogger(__name__)


class EmailEvidenceClassification(BaseModel):
    """Schema for Gemini email classification output."""
    email: str
    source_type: str = Field(description="'publicly_published' or 'inferred'")
    confidence: str = Field(description="'high', 'medium', or 'low'")
    is_valid_contact: bool = Field(description="True if this email is a legitimate contact for the creator")
    reasoning: str = Field(description="Short reason for classification")


class ProfileVerificationResult(BaseModel):
    """Schema for Gemini profile & evidence reasoning."""
    selected_primary_email: Optional[str] = None
    classified_emails: List[EmailEvidenceClassification] = Field(default_factory=list)
    verified_socials: List[Dict[str, str]] = Field(default_factory=list)


async def classify_and_verify_with_gemini(
    creator_name: str,
    channel_name: str,
    video_title: str,
    description: str,
    raw_socials: List[SocialProfile],
    raw_emails: List[EmailCandidate],
) -> Optional[ProfileVerificationResult]:
    """Use Google Gemini to reason over extracted evidence and classify email authenticity."""
    if not settings.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not configured. Using deterministic fallback classification.")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        system_prompt = (
            "You are an expert AI research agent specialized in creator contact intelligence. "
            "Your task is to analyze candidate emails and social profiles discovered for a YouTube creator, "
            "and rigorously verify and classify them.\n\n"
            "STRICT RULES:\n"
            "1. NEVER invent or hallucinate an email. If none of the candidates are legitimate, return null for selected_primary_email.\n"
            "2. Distinguish between 'publicly_published' (explicitly stated on YouTube or website) vs 'inferred' (guessed from domain).\n"
            "3. Reject sponsor/affiliate emails (e.g. support@expressvpn.com, contact@squarespace.com, discounts@brand.com).\n"
            "4. Assign email confidence:\n"
            "   - 'high': Publicly published specifically for business, management, or creator contact.\n"
            "   - 'medium': Publicly found on creator's personal website or bio.\n"
            "   - 'low': Inferred, guessed, or ambiguous.\n"
            "5. SOCIAL PROFILES: ONLY verify and return profiles for these platforms: 'Instagram', 'X', 'LinkedIn', 'Facebook', 'Discord', 'Reddit', 'TikTok'. Do NOT include any other platforms.\n"
            "6. Return valid JSON matching the requested structure."
        )

        user_content = {
            "creator_name": creator_name,
            "channel_name": channel_name,
            "video_title": video_title,
            "video_description_excerpt": description[:1500] if description else "",
            "candidate_emails": [e.model_dump() for e in raw_emails],
            "candidate_social_profiles": [s.model_dump() for s in raw_socials]
        }

        prompt = f"Analyze this creator data and output JSON:\n```json\n{json.dumps(user_content, indent=2)}\n```\n\nReturn a JSON object with keys: 'selected_primary_email' (str or null), 'classified_emails' (array of objects with 'email', 'source_type', 'confidence', 'is_valid_contact', 'reasoning'), and 'verified_socials' (array of objects with 'platform', 'username', 'url', 'confidence')."

        # Try gemini models with resilient fallback
        response_text = ""
        for model_name in ["gemini-3.6-flash", "gemini-flash-latest"]:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                if resp and resp.text:
                    response_text = resp.text.strip()
                    break
            except Exception as e:
                logger.warning(f"Failed with model {model_name}: {e}")
                continue

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
        allowed_platforms = {"Instagram", "X", "Discord", "Reddit", "Facebook"}
        filtered_verified_socials = [
            s for s in parsed.get("verified_socials", [])
            if s.get("platform") in allowed_platforms
        ]

        return ProfileVerificationResult(
            selected_primary_email=parsed.get("selected_primary_email"),
            classified_emails=classified_list,
            verified_socials=filtered_verified_socials
        )

    except Exception as e:
        logger.error(f"Gemini reasoning error: {e}", exc_info=True)
        return None
