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
DEFAULT_LINKED_PLATFORM: str = "Instagram"

# Internal mutable holder allowing overrides during testing without modifying production code.
_current_linked_account: Optional[str] = LINKED_INSTAGRAM_ACCOUNT
_current_linked_platform: Optional[str] = DEFAULT_LINKED_PLATFORM


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
    """
    return normalize_instagram_username(_current_linked_account)


def get_linked_platform() -> Optional[str]:
    """Retrieve the platform of the linked Arclent account ('Instagram', 'X', etc.)."""
    if not _current_linked_account:
        return None
    return _current_linked_platform or "Instagram"


def set_dummy_linked_instagram_account(username: Optional[str]) -> None:
    """Helper function to override the dummy linked Instagram account for unit testing."""
    global _current_linked_account, _current_linked_platform
    _current_linked_account = username
    _current_linked_platform = "Instagram" if username else None


def set_dummy_linked_account(username: Optional[str], platform: Optional[str] = "Instagram") -> None:
    """Helper function to override the dummy linked account and its platform for testing."""
    global _current_linked_account, _current_linked_platform
    _current_linked_account = username
    _current_linked_platform = platform if username else None


def reset_dummy_linked_instagram_account() -> None:
    """Reset the dummy linked account back to the default 'ummer.04' on 'Instagram'."""
    global _current_linked_account, _current_linked_platform
    _current_linked_account = LINKED_INSTAGRAM_ACCOUNT
    _current_linked_platform = DEFAULT_LINKED_PLATFORM
