"""Linked Arclent Account Module.

Represents the creator's social account linked to their Arclent profile.
For the initial implementation of the automatic description verification feature,
this module provides a dummy linked account ("ummer.04") that can later be replaced
with the authenticated user's actual linked account (e.g. current_user.instagram_username)
without modifying any core verification logic.
"""

from typing import Optional


# Default dummy linked account for testing and demonstration.
# In production with account-linking enabled, this will be retrieved from the user session/DB.
LINKED_INSTAGRAM_ACCOUNT: str = "ummer.04"

# Internal mutable holder allowing overrides during testing without modifying production code.
_current_linked_account: Optional[str] = LINKED_INSTAGRAM_ACCOUNT


def normalize_instagram_username(username: Optional[str]) -> Optional[str]:
    """Normalize an Instagram username by stripping '@', whitespace, and converting to lowercase."""
    if not username:
        return None
    cleaned = username.strip().lstrip("@").rstrip("/").strip().lower()
    return cleaned if cleaned else None


def get_linked_instagram_account() -> Optional[str]:
    """Retrieve the currently linked Instagram account for the Arclent creator.
    
    Returns:
        Normalized Instagram username (e.g. 'ummer.04'), or None if not linked.
        
    Note:
        To integrate with real Arclent user authentication in the future, replace the
        return statement below with:
            return normalize_instagram_username(current_user.instagram_username)
    """
    return normalize_instagram_username(_current_linked_account)


def set_dummy_linked_instagram_account(username: Optional[str]) -> None:
    """Helper function to override the dummy linked Instagram account for unit testing."""
    global _current_linked_account
    _current_linked_account = username


def reset_dummy_linked_instagram_account() -> None:
    """Reset the dummy linked Instagram account back to the default 'ummer.04'."""
    global _current_linked_account
    _current_linked_account = LINKED_INSTAGRAM_ACCOUNT
