"""Pydantic schemas for API request and response validation."""

from typing import List, Optional, Literal, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class OutreachStage(str, Enum):
    """Explicit workflow stages for creator outreach."""
    INPUT = "input"
    DISCOVERING = "discovering"
    VERIFY_EMAIL = "verify_email"
    VERIFY_INSTAGRAM = "verify_instagram"
    OUTREACH_HUB = "outreach_hub"
    CREATOR_FOUND = "creator_found"
    NO_EMAIL_CHOICE = "no_email_choice"
    MANUAL_EMAIL_INPUT = "manual_email_input"
    MESSAGE_DRAFT = "message_draft"
    INSTAGRAM_READY = "instagram_ready"
    MANUAL_MESSAGE_READY = "manual_message_ready"
    SENT = "sent"
    AUTO_VERIFIED = "auto_verified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ResearchRequest(BaseModel):
    """Incoming request to discover creator details from a YouTube URL."""
    youtube_url: str = Field(..., description="Full YouTube video URL or channel link")
    user_role: Optional[str] = Field(default="Video editor", description="Role on the piece of content")
    linked_instagram_account: Optional[str] = Field(default=None, description="Optional linked Instagram handle of the contributor")

    @field_validator("youtube_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("YouTube URL cannot be empty")
        # Accept youtube.com, youtu.be, or direct channel handles starting with @ or channel names
        if "youtube.com" not in v and "youtu.be" not in v and not v.startswith("@"):
            raise ValueError("Please enter a valid YouTube video or channel URL")
        return v


class SocialProfile(BaseModel):
    """Discovered social media account."""
    platform: str = Field(..., description="Social platform name (Instagram, X, Discord, Reddit, Facebook, Twitch)")
    username: str = Field(..., description="Handle or username")
    url: str = Field(..., description="Full URL to public profile")
    source: str = Field(default="YouTube description", description="Source where profile was identified")
    confidence: Literal["high", "medium", "low"] = Field(default="medium", description="Confidence level")


class EmailCandidate(BaseModel):
    """Discovered or evaluated email candidate."""
    email: str = Field(..., description="Email address")
    source: str = Field(..., description="Source location (e.g. YouTube description, Creator Website → Contact)")
    source_type: Literal["publicly_published", "inferred", "manual"] = Field(
        default="publicly_published", 
        description="Classification of email origin"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="high", 
        description="Confidence score for authenticity"
    )
    context: Optional[str] = Field(default=None, description="Contextual snippet around the email")
    verification_status: Optional[str] = Field(default="verified_evidence", description="Status description")


class OutreachMessage(BaseModel):
    """Structured outreach message object."""
    recipient_name: str
    subject: Optional[str] = None
    body: str
    channel: Literal["email", "instagram", "manual"] = "email"


class CreatorProfile(BaseModel):
    """Creator identity information."""
    name: str
    channel_name: str
    channel_handle: Optional[str] = None
    channel_url: Optional[str] = None
    profile_image: Optional[str] = None
    subscriber_count: Optional[str] = None
    video_title: Optional[str] = None
    video_url: Optional[str] = None
    description: Optional[str] = None
    channel_description: Optional[str] = None
    video_description: Optional[str] = None
    channel_links: List[str] = Field(default_factory=list)


class AutoVerificationResult(BaseModel):
    """Result of the automatic YouTube description contributor verification."""
    verified: bool = Field(..., description="Whether the contribution was automatically verified")
    status: str = Field(
        ..., 
        description="Verification outcome code: 'auto_verified', 'fallback_no_match', 'fallback_no_instagram', 'fallback_empty_description', 'fallback_no_linked_account'"
    )
    method: Optional[str] = Field(
        default=None, 
        description="Verification method identifier when successful ('youtube_description_instagram_match')"
    )
    matched_account: Optional[str] = Field(
        default=None, 
        description="The normalized Instagram username that matched"
    )
    linked_account: Optional[str] = Field(
        default=None, 
        description="The normalized linked Arclent Instagram account tested"
    )
    extracted_accounts: List[str] = Field(
        default_factory=list, 
        description="All Instagram accounts identified in the video description"
    )
    reason: str = Field(..., description="Human-readable explanation of the outcome")


class OutreachSession(BaseModel):
    """Complete state container for an outreach workflow session."""
    session_id: str
    youtube_url: str
    stage: OutreachStage = OutreachStage.INPUT
    user_role: Optional[str] = "Video editor"
    creator: Optional[CreatorProfile] = None
    discovered_email: Optional[EmailCandidate] = None
    creator_confirmed: Optional[bool] = None
    email_confirmed: Optional[bool] = None
    final_email: Optional[str] = None
    email_source: Optional[str] = None
    email_confidence: Optional[str] = None
    email_verification_status: Optional[str] = None
    social_profiles: List[SocialProfile] = Field(default_factory=list)
    instagram_profile: Optional[SocialProfile] = None
    instagram_confirmed: Optional[bool] = None
    final_instagram_handle: Optional[str] = None
    final_instagram_url: Optional[str] = None
    auto_verification: Optional[AutoVerificationResult] = None
    message: Optional[OutreachMessage] = None
    selected_channel: Optional[str] = None
    sender_identity: Optional[str] = None
    sender_handle: Optional[str] = None
    sender_email: Optional[str] = None
    sender_platform: Optional[str] = None
    creator_response: Optional[Literal["pending", "confirmed", "rejected"]] = "pending"
    verified_at: Optional[str] = None
    verification_token: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Raw Graph Pipeline Output Model
# ------------------------------------------------------------------------------

class RawCreatorResearchResult(BaseModel):
    """Raw output of the LangGraph creator research pipeline."""
    video_url: str
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    creator_name: str = "Creator"
    channel_name: str = "Channel"
    channel_handle: Optional[str] = None
    channel_url: Optional[str] = None
    profile_image: Optional[str] = None
    subscriber_count: Optional[str] = None
    description: Optional[str] = None
    channel_description: Optional[str] = None
    video_description: Optional[str] = None
    channel_links: List[str] = Field(default_factory=list)
    published_at: Optional[str] = None
    social_profiles: List[SocialProfile] = Field(default_factory=list)
    email_candidates: List[EmailCandidate] = Field(default_factory=list)
    selected_email: Optional[str] = None
    email_source: Optional[str] = None
    email_confidence: Optional[str] = None
    email_source_type: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Workflow Step Request / Response Models
# ------------------------------------------------------------------------------

class ConfirmCreatorRequest(BaseModel):
    """User confirmation decision for discovered creator."""
    session_id: str
    creator_confirmed: bool
    user_role: Optional[str] = None


class ConfirmEmailRequest(BaseModel):
    """Step 1: User confirmation decision for discovered email."""
    session_id: str
    email_confirmed: bool
    user_role: Optional[str] = None


class ConfirmInstagramRequest(BaseModel):
    """Step 2: User confirmation decision for discovered Instagram."""
    session_id: str
    instagram_confirmed: bool
    user_role: Optional[str] = None


class ManualInstagramRequest(BaseModel):
    """Manual Instagram handle submission payload."""
    session_id: str
    handle: str
    user_role: Optional[str] = None

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Instagram handle cannot be empty.")
        if v.startswith("https://") or v.startswith("http://"):
            # Extract handle from URL if user pasted a link
            parts = v.rstrip("/").split("/")
            v = parts[-1]
        v = v.lstrip("@").strip()
        if not v:
            raise ValueError("Please enter a valid Instagram handle.")
        return f"@{v}"


class ManualEmailRequest(BaseModel):
    """Manual email submission payload."""
    session_id: str
    email: str
    user_role: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_manual_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v or "." not in v or len(v.split("@")) != 2:
            raise ValueError("Please enter a valid email address.")
        user, domain = v.split("@")
        if not user or not domain or len(domain.split(".")) < 2:
            raise ValueError("Please enter a valid email address.")
        return v


class GenerateMessageRequest(BaseModel):
    """Request to generate/regenerate an outreach message."""
    session_id: str
    channel: Literal["email", "instagram", "manual"] = "email"
    user_role: Optional[str] = None
    custom_notes: Optional[str] = None


class SendEmailRequest(BaseModel):
    """Request payload to send an email."""
    recipient: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Plain text email body")


class SendEmailWorkflowRequest(BaseModel):
    """Request to send email via connected Gmail account."""
    session_id: str
    recipient: Optional[str] = None
    subject: str = Field(default="Collaboration Opportunity")
    body: str


class RecordSocialOutreachRequest(BaseModel):
    """Request to record social media outreach dispatch."""
    session_id: str
    platform: Optional[str] = "Instagram"
    handle: Optional[str] = None
    sender_handle: Optional[str] = None
    sender_identity: Optional[str] = None
    message: Optional[str] = None


class CreatorDiscoveryResponse(BaseModel):
    """Discovery response payload for workflow."""
    session_id: str
    stage: OutreachStage
    creator: CreatorProfile
    discovered_email: Optional[EmailCandidate] = None
    has_reliable_email: bool
    social_profiles: List[SocialProfile] = Field(default_factory=list)
    instagram_profile: Optional[SocialProfile] = None
    auto_verification: Optional[AutoVerificationResult] = None
    errors: List[str] = Field(default_factory=list)


class GmailStatusResponse(BaseModel):
    """Status of the Gmail OAuth integration."""
    connected: bool
    email: Optional[str] = None
    scopes: Optional[List[str]] = None


class SendEmailResponse(BaseModel):
    """Response returned after sending an email via Gmail API."""
    success: bool
    message: str
    recipient: str
    message_id: Optional[str] = None
    sender: Optional[str] = None
    timestamp: Optional[str] = None
