"""Backward compatibility module: Redirects Gemini service calls to Mistral AI."""

from app.services.mistral_service import (
    EmailEvidenceClassification,
    ProfileVerificationResult,
    classify_and_verify_with_mistral,
    classify_and_verify_with_gemini,
)

__all__ = [
    "EmailEvidenceClassification",
    "ProfileVerificationResult",
    "classify_and_verify_with_mistral",
    "classify_and_verify_with_gemini",
]
