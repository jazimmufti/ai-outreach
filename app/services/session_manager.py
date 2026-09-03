"""In-memory thread-safe session manager for outreach workflows."""

import time
import uuid
import threading
import logging
from typing import Optional, Dict

from app.models.schemas import OutreachSession, OutreachStage

logger = logging.getLogger(__name__)

_sessions: Dict[str, Dict[str, any]] = {}
_session_lock = threading.Lock()
SESSION_TTL_SECONDS = 3600  # 1 hour


def _cleanup_expired_sessions() -> None:
    """Evict expired sessions."""
    now = time.time()
    with _session_lock:
        expired = [
            sid for sid, data in _sessions.items()
            if now - data.get("updated_at", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            _sessions.pop(sid, None)


def create_session(youtube_url: str) -> OutreachSession:
    """Create and register a new outreach workflow session."""
    _cleanup_expired_sessions()
    session_id = f"outreach_{uuid.uuid4().hex[:12]}"
    session = OutreachSession(
        session_id=session_id,
        youtube_url=youtube_url,
        stage=OutreachStage.DISCOVERING
    )
    with _session_lock:
        _sessions[session_id] = {
            "session": session,
            "updated_at": time.time()
        }
    return session


def get_session(session_id: str) -> Optional[OutreachSession]:
    """Retrieve an active outreach workflow session."""
    _cleanup_expired_sessions()
    with _session_lock:
        entry = _sessions.get(session_id)
        if entry:
            entry["updated_at"] = time.time()
            return entry["session"]
    return None


def save_session(session: OutreachSession) -> None:
    """Save/update an outreach workflow session."""
    _cleanup_expired_sessions()
    with _session_lock:
        _sessions[session.session_id] = {
            "session": session,
            "updated_at": time.time()
        }


def delete_session(session_id: str) -> None:
    """Remove a session."""
    with _session_lock:
        _sessions.pop(session_id, None)


def clear_all_sessions() -> None:
    """Clear all active sessions."""
    with _session_lock:
        _sessions.clear()


def get_most_recent_session() -> Optional[OutreachSession]:
    """Retrieve the most recently active session."""
    _cleanup_expired_sessions()
    with _session_lock:
        if not _sessions:
            return None
        latest_entry = max(_sessions.values(), key=lambda x: x.get("updated_at", 0))
        return latest_entry.get("session")

