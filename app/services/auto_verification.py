"""Automatic Contribution Verification Service.

Matches extracted Instagram contributor mentions from a YouTube video description
against the creator's linked Arclent Instagram account.
Provides a clear verification status, method, matched account, and reason.
"""

from typing import List, Optional

from app.models.schemas import AutoVerificationResult
from app.services.linked_account import get_linked_instagram_account, normalize_instagram_username
from app.services.youtube_description_parser import (
    extract_credit_candidates,
    extract_verified_contributor_accounts
)


def verify_contribution_from_description(
    description: Optional[str],
    linked_account: Optional[str] = None,
    user_role: Optional[str] = None,
    verified_accounts: Optional[List[str]] = None
) -> AutoVerificationResult:
    """Verify whether a creator's contribution is credited in the YouTube description.
    
    Args:
        description: Raw YouTube video description.
        linked_account: Optional override for the creator's linked Instagram handle.
                        If omitted, uses get_linked_instagram_account().
        user_role: Role selected by user (e.g. 'Video editor', 'Thumbnail designer').
                   Credits are strictly filtered to match this role.
        verified_accounts: Optional pre-verified list of accounts known to exist on the platform.
                        
    Returns:
        AutoVerificationResult with detailed match info, status, and human-readable explanation.
    """
    # 1. Check if linked account is available
    if linked_account is not None:
        active_linked = normalize_instagram_username(linked_account)
    else:
        active_linked = get_linked_instagram_account()
    
    # Extract accounts matching role
    if verified_accounts is not None:
        extracted = list(verified_accounts)
    else:
        candidates = extract_credit_candidates(description, user_role=user_role)
        extracted = [c["username"] for c in candidates if c.get("username")]

    if not active_linked:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_linked_account",
            method=None,
            matched_account=None,
            linked_account=None,
            extracted_accounts=extracted,
            reason="No linked Instagram account found on your Arclent profile. Continuing to existing verification."
        )

    # 2. Check if description is empty
    if not description or not description.strip():
        return AutoVerificationResult(
            verified=False,
            status="fallback_empty_description",
            method=None,
            matched_account=None,
            linked_account=active_linked,
            extracted_accounts=[],
            reason="YouTube description is empty or unavailable. Continuing to existing verification."
        )

    # 3. Check if any accounts were found
    if not extracted:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_instagram",
            method=None,
            matched_account=None,
            linked_account=active_linked,
            extracted_accounts=[],
            reason="No Instagram accounts detected in the video description. Continuing to existing verification."
        )

    # 4. Check for match
    if active_linked in extracted:
        return AutoVerificationResult(
            verified=True,
            status="auto_verified",
            method="youtube_description_instagram_match",
            matched_account=active_linked,
            linked_account=active_linked,
            extracted_accounts=extracted,
            reason=f"Linked Instagram account @{active_linked} was found in the video's contributor information."
        )

    # 5. Accounts found, but none match linked account
    accounts_preview = ", ".join(f"@{acc}" for acc in extracted[:3])
    if len(extracted) > 3:
        accounts_preview += f" (+{len(extracted) - 3} more)"

    return AutoVerificationResult(
        verified=False,
        status="fallback_no_match",
        method=None,
        matched_account=None,
        linked_account=active_linked,
        extracted_accounts=extracted,
        reason=f"Detected Instagram account(s) {accounts_preview}, but none match your linked account @{active_linked}. Continuing to existing verification."
    )


async def verify_contribution_from_description_async(
    description: Optional[str],
    linked_account: Optional[str] = None,
    user_role: Optional[str] = None
) -> AutoVerificationResult:
    """Async verification that strictly verifies candidate existence on Instagram before matching."""
    if not description or not description.strip():
        return verify_contribution_from_description(
            description,
            linked_account=linked_account,
            user_role=user_role,
            verified_accounts=[]
        )

    verified_contribs = await extract_verified_contributor_accounts(
        description,
        linked_platform="Instagram",
        linked_account=linked_account,
        user_role=user_role
    )
    verified_handles = [
        c["username"] for c in verified_contribs
        if "Instagram" in c.get("platforms", []) and c.get("username")
    ]
    return verify_contribution_from_description(
        description,
        linked_account=linked_account,
        user_role=user_role,
        verified_accounts=verified_handles
    )
