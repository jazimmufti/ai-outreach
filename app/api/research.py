"""Research API endpoints for Creator Discovery."""

import json
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.schemas import ResearchRequest, RawCreatorResearchResult
from app.workflows.creator_research_graph import (
    execute_creator_research,
    execute_creator_research_stream
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["research"])


@router.post("/research", response_model=RawCreatorResearchResult)
async def research_creator_endpoint(payload: ResearchRequest):
    """Analyze YouTube URL and discover creator profile, social links, and public emails."""
    try:
        result = await execute_creator_research(payload.youtube_url)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error during creator research: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research processing failed: {str(e)}")


@router.get("/research/stream")
async def stream_research_creator_endpoint(youtube_url: str = Query(..., description="YouTube video URL")):
    """Server-Sent Events (SSE) endpoint to stream real-time research progress to UI."""
    if not youtube_url:
        raise HTTPException(status_code=400, detail="Missing required 'youtube_url' parameter")

    async def event_generator():
        try:
            async for event in execute_creator_research_stream(youtube_url):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            err_payload = {
                "step": -1,
                "status": "error",
                "error": f"Internal pipeline error: {str(e)}"
            }
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
