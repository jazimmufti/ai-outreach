"""Automatic Contribution Verification Service.

Matches extracted Instagram contributor mentions from a YouTube video description
against the creator's linked Arclent Instagram account.
Provides a clear verification status, method, matched account, and reason.
"""

from typing import List, Optional

from app.models.schemas import AutoVerificationResult
from app.services.linked_account import get_linked_instagram_account, normalize_instagram_username
from app.services.youtube_description_parser import extract_instagram_accounts


def verify_contribution_from_description(
    description: Optional[str],
    linked_account: Optional[str] = None
) -> AutoVerificationResult:
    """Verify whether a creator's contribution is credited in the YouTube description.
    
    Args:
        description: Raw YouTube video description.
        linked_account: Optional override for the creator's linked Instagram handle.
                        If omitted, uses get_linked_instagram_account().
                        
    Returns:
        AutoVerificationResult with detailed match info, status, and human-readable explanation.
    """
    # 1. Check if linked account is available
    if linked_account is not None:
        active_linked = normalize_instagram_username(linked_account)
    else:
        active_linked = get_linked_instagram_account()
    
    if not active_linked:
        extracted = extract_instagram_accounts(description) if description else []
        try:
            from app.services.youtube_description_parser import extract_credit_candidates
            for c in extract_credit_candidates(description):
                u = c["username"]
                if u and u not in extracted:
                    extracted.append(u)
        except Exception:
            pass
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

    # 3. Extract candidate handles from Instagram links, prefixes, and credit mentions (editor: @username, etc.)
    extracted_accounts = extract_instagram_accounts(description)
    try:
        from app.services.youtube_description_parser import extract_credit_candidates
        for c in extract_credit_candidates(description):
            u = c["username"]
            if u and u not in extracted_accounts:
                extracted_accounts.append(u)
    except Exception:
        pass

    # 4. Check if any accounts were found
    if not extracted_accounts:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_instagram",
            method=None,
            matched_account=None,
            linked_account=active_linked,
            extracted_accounts=[],
            reason="No Instagram accounts detected in the video description. Continuing to existing verification."
        )

    # 5. Check for match
    if active_linked in extracted_accounts:
        return AutoVerificationResult(
            verified=True,
            status="auto_verified",
            method="youtube_description_instagram_match",
            matched_account=active_linked,
            linked_account=active_linked,
            extracted_accounts=extracted_accounts,
            reason=f"Linked Instagram account @{active_linked} was found in the video's contributor information."
        )

    # 6. Accounts found, but none match linked account
    accounts_preview = ", ".join(f"@{acc}" for acc in extracted_accounts[:3])
    if len(extracted_accounts) > 3:
        accounts_preview += f" (+{len(extracted_accounts) - 3} more)"

    return AutoVerificationResult(
        verified=False,
        status="fallback_no_match",
        method=None,
        matched_account=None,
        linked_account=active_linked,
        extracted_accounts=extracted_accounts,
        reason=f"Detected Instagram account(s) {accounts_preview}, but none match your linked account @{active_linked}. Continuing to existing verification."
    )
