import os
import json
import time
import uuid
import threading
import logging
from typing import Optional, Dict

from app.models.schemas import OutreachSession, OutreachStage

logger = logging.getLogger(__name__)

_sessions: Dict[str, Dict[str, any]] = {}
_session_lock = threading.Lock()
SESSION_TTL_SECONDS = 86400 * 14  # 14 days
SESSION_STORE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".sessions_store.json")


def _load_sessions_from_disk() -> None:
    """Load persistent sessions from disk on startup."""
    if not os.path.exists(SESSION_STORE_FILE):
        return
    try:
        with open(SESSION_STORE_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            now = time.time()
            for sid, item in raw_data.items():
                updated_at = item.get("updated_at", 0)
                if now - updated_at <= SESSION_TTL_SECONDS:
                    session_obj = OutreachSession.model_validate(item["session"])
                    _sessions[sid] = {
                        "session": session_obj,
                        "updated_at": updated_at
                    }
    except Exception as e:
        logger.warning(f"Could not load persistent sessions: {e}")


def _save_sessions_to_disk() -> None:
    """Persist active sessions to disk."""
    try:
        serialized = {}
        for sid, item in _sessions.items():
            serialized[sid] = {
                "session": item["session"].model_dump(),
                "updated_at": item["updated_at"]
            }
        with open(SESSION_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(serialized, f)
    except Exception as e:
        logger.warning(f"Could not persist sessions to disk: {e}")


# Initialize from disk
_load_sessions_from_disk()


def _cleanup_expired_sessions() -> None:
    """Evict expired sessions."""
    now = time.time()
    with _session_lock:
        expired = [
            sid for sid, data in _sessions.items()
            if now - data.get("updated_at", 0) > SESSION_TTL_SECONDS
        ]
        if expired:
            for sid in expired:
                _sessions.pop(sid, None)
            _save_sessions_to_disk()


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
        _save_sessions_to_disk()
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
        _save_sessions_to_disk()


def delete_session(session_id: str) -> None:
    """Remove a session."""
    with _session_lock:
        _sessions.pop(session_id, None)
        _save_sessions_to_disk()


def clear_all_sessions() -> None:
    """Clear all active sessions."""
    with _session_lock:
        _sessions.clear()
        if os.path.exists(SESSION_STORE_FILE):
            try:
                os.remove(SESSION_STORE_FILE)
            except Exception:
                pass


def get_most_recent_session() -> Optional[OutreachSession]:
    """Retrieve the most recently active session."""
    _cleanup_expired_sessions()
    with _session_lock:
        if not _sessions:
            return None
        latest_entry = max(_sessions.values(), key=lambda x: x.get("updated_at", 0))
        return latest_entry.get("session")


