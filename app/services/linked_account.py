"""Linked Arclent Account Module.

Represents the creator's social account linked to their Arclent profile.
For the initial implementation of the automatic description verification feature,
this module provides a dummy linked account ("ummer.04") that can later be replaced
with the authenticated user's actual linked account (e.g. current_user.instagram_username)
without modifying any core verification logic.
"""

from typing import Optional


# Default linked account for Arclent profile.
# By default, NO Instagram account is connected initially.
LINKED_INSTAGRAM_ACCOUNT: Optional[str] = None
DEFAULT_LINKED_PLATFORM: Optional[str] = None

# Default linked Discord account for Arclent sender/creator
DEFAULT_LINKED_DISCORD_ACCOUNT: Optional[str] = "151600386127968346"

# Internal mutable holder allowing overrides during testing without modifying production code.
_current_linked_account: Optional[str] = LINKED_INSTAGRAM_ACCOUNT
_current_linked_platform: Optional[str] = DEFAULT_LINKED_PLATFORM
_current_linked_discord_account: Optional[str] = DEFAULT_LINKED_DISCORD_ACCOUNT


def normalize_instagram_username(username: Optional[str]) -> Optional[str]:
    """Normalize an Instagram username by stripping '@', whitespace, and converting to lowercase."""
    if not username:
        return None
    cleaned = username.strip().lstrip("@").rstrip("/").strip().lower()
    return cleaned if cleaned else None


def normalize_discord_account(account: Optional[str]) -> Optional[str]:
    """Normalize a Discord account (snowflake ID or username)."""
    if not account:
        return None
    cleaned = account.strip().lstrip("@").rstrip("/").strip().lower()
    return cleaned if cleaned else None


def get_linked_instagram_account() -> Optional[str]:
    """Retrieve the currently linked Instagram account for the Arclent creator.
    
    Returns:
        Normalized Instagram username (e.g. 'ummer.04'), or None if not linked.
    """
    return normalize_instagram_username(_current_linked_account)


def get_linked_discord_account() -> Optional[str]:
    """Retrieve the currently linked Discord account (ID or username) for the Arclent user.
    
    Returns:
        Normalized Discord account (e.g. '151600386127968346'), or None if not linked.
    """
    return normalize_discord_account(_current_linked_discord_account)


def get_linked_account(platform: Optional[str] = None) -> Optional[str]:
    """Retrieve linked account for given platform ('Instagram', 'Discord', etc.)."""
    plat = (platform or get_linked_platform() or "Instagram").lower()
    if "discord" in plat:
        return get_linked_discord_account()
    return get_linked_instagram_account()


def get_linked_platform() -> Optional[str]:
    """Retrieve the platform of the linked Arclent account ('Instagram', 'Discord', 'X', etc.)."""
    if not _current_linked_account and _current_linked_discord_account:
        return "Discord"
    if not _current_linked_account:
        return None
    return _current_linked_platform or "Instagram"


def set_dummy_linked_instagram_account(username: Optional[str]) -> None:
    """Helper function to override the dummy linked Instagram account for unit testing."""
    global _current_linked_account, _current_linked_platform
    _current_linked_account = username
    _current_linked_platform = "Instagram" if username else None


def set_dummy_linked_discord_account(account: Optional[str]) -> None:
    """Helper function to override the dummy linked Discord account for testing."""
    global _current_linked_discord_account
    _current_linked_discord_account = account


def set_dummy_linked_account(username: Optional[str], platform: Optional[str] = "Instagram") -> None:
    """Helper function to override the dummy linked account and its platform for testing."""
    global _current_linked_account, _current_linked_platform, _current_linked_discord_account
    if platform and "discord" in platform.lower():
        _current_linked_discord_account = username
    else:
        _current_linked_account = username
        _current_linked_platform = platform if username else None


def reset_dummy_linked_instagram_account() -> None:
    """Reset the dummy linked account back to None (unlinked)."""
    global _current_linked_account, _current_linked_platform
    _current_linked_account = LINKED_INSTAGRAM_ACCOUNT
    _current_linked_platform = DEFAULT_LINKED_PLATFORM


def reset_dummy_linked_discord_account() -> None:
    """Reset the dummy linked Discord account back to default ('151600386127968346')."""
    global _current_linked_discord_account
    _current_linked_discord_account = DEFAULT_LINKED_DISCORD_ACCOUNT

