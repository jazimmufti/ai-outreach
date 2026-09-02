"""Email sending API routes."""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.schemas import SendEmailRequest, SendEmailResponse
from app.services.gmail_service import send_test_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/email", tags=["email"])


@router.post("/send", response_model=SendEmailResponse)
async def send_email_endpoint(payload: SendEmailRequest):
    """Send an outreach email to the specified recipient via the connected Gmail account."""
    try:
        result = send_test_email(
            recipient=payload.recipient,
            subject=payload.subject,
            body=payload.body
        )
        return SendEmailResponse(
            success=True,
            message="Test email sent successfully",
            recipient=result["recipient"],
            sender=result.get("sender"),
            message_id=result.get("message_id"),
            timestamp=result.get("timestamp", datetime.utcnow().isoformat())
        )
    except ValueError as ve:
        # e.g. not connected or invalid recipient
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
