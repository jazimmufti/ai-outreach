"""Automatic Contribution Verification Service.

Matches extracted Instagram and Discord contributor mentions from a YouTube video description
against the creator's linked Arclent Instagram or Discord account.
Provides a clear verification status, method, matched account, and reason.
"""

import re
from typing import List, Optional

from app.models.schemas import AutoVerificationResult
from app.services.linked_account import (
    get_linked_instagram_account,
    normalize_instagram_username,
    get_linked_discord_account,
    normalize_discord_account
)
from app.services.youtube_description_parser import (
    extract_credit_candidates,
    extract_verified_contributor_accounts,
    extract_discord_credit_candidates
)


def verify_contribution_from_description(
    description: Optional[str],
    linked_account: Optional[str] = None,
    linked_discord_account: Optional[str] = None,
    user_role: Optional[str] = None,
    verified_accounts: Optional[List[str]] = None
) -> AutoVerificationResult:
    """Verify whether a creator's contribution is credited in the YouTube description.
    
    Supports both Instagram and Discord linked accounts:
    - Discord: matches user snowflake ID or Discord username
    - Instagram: matches Instagram handle or credited name
    
    Args:
        description: Raw YouTube video description.
        linked_account: Optional override for the creator's linked Instagram handle (or generic linked account).
        linked_discord_account: Optional override for the creator's linked Discord user ID or username.
        user_role: Role selected by user (e.g. 'Video editor', 'Thumbnail designer').
                   Credits are strictly filtered to match this role.
        verified_accounts: Optional pre-verified list of accounts known to exist on the platform.
                        
    Returns:
        AutoVerificationResult with detailed match info, status, and human-readable explanation.
    """
    def normalize_for_comparison(val: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", val or "").lower()

    # 1. Resolve linked accounts
    active_ig = normalize_instagram_username(linked_account) if linked_account is not None else get_linked_instagram_account()
    active_discord = normalize_discord_account(linked_discord_account) if linked_discord_account is not None else get_linked_discord_account()

    # If linked_account was passed and looks like a Discord snowflake ID (17-20 digits) or Discord syntax
    if linked_account and not active_discord:
        norm_disc = normalize_discord_account(linked_account)
        if norm_disc and (re.match(r"^[0-9]{17,20}$", norm_disc) or "discord" in linked_account.lower()):
            active_discord = norm_disc

    # 2. Check if description is empty
    if not description or not description.strip():
        primary_linked = active_ig or active_discord
        return AutoVerificationResult(
            verified=False,
            status="fallback_empty_description",
            method=None,
            matched_account=None,
            linked_account=primary_linked,
            extracted_accounts=[],
            reason="YouTube description is empty or unavailable. Continuing to existing verification."
        )

    # 3. Extract candidates
    if verified_accounts is not None:
        extracted_ig = list(verified_accounts)
    else:
        ig_candidates = extract_credit_candidates(description, user_role=user_role)
        extracted_ig = [c["username"] for c in ig_candidates if c.get("username") and c.get("specified_platform") != "Discord"]

    discord_candidates = extract_discord_credit_candidates(description, user_role=user_role)

    # Combine extracted account identifiers for diagnostics
    extracted_combined: List[str] = list(extracted_ig)
    for dc in discord_candidates:
        cid = dc.get("discord_user_id") or dc.get("discord_username")
        if cid and cid not in extracted_combined:
            extracted_combined.append(cid)

    # Check if any linked account is configured
    if not active_ig and not active_discord:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_linked_account",
            method=None,
            matched_account=None,
            linked_account=None,
            extracted_accounts=extracted_combined,
            reason="No linked account found on your Arclent profile. Continuing to existing verification."
        )

    if not active_ig and not discord_candidates and extracted_ig:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_linked_account",
            method=None,
            matched_account=None,
            linked_account=None,
            extracted_accounts=extracted_combined,
            reason="No linked Instagram account found on your Arclent profile. Continuing to existing verification."
        )

    if not active_discord and not extracted_ig and discord_candidates:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_linked_account",
            method=None,
            matched_account=None,
            linked_account=None,
            extracted_accounts=extracted_combined,
            reason="No linked Discord account found on your Arclent profile. Continuing to existing verification."
        )

    # 4. Attempt Discord Match
    if active_discord and discord_candidates:
        active_disc_norm = normalize_for_comparison(active_discord)
        for dc in discord_candidates:
            cid = dc.get("discord_user_id")
            cname = dc.get("discord_username")
            raw = dc.get("raw_credit") or ""

            is_match = False
            # Check snowflake ID match
            if cid and (cid == active_discord or normalize_discord_account(raw) == active_discord):
                is_match = True
            # Check username match
            elif cname and (cname == active_discord or normalize_for_comparison(cname) == active_disc_norm):
                is_match = True

            if is_match:
                matched_val = cid if (cid and cid == active_discord) else (cname or active_discord)
                return AutoVerificationResult(
                    verified=True,
                    status="auto_verified",
                    method="youtube_description_discord_match",
                    matched_account=matched_val,
                    linked_account=active_discord,
                    extracted_accounts=extracted_combined,
                    reason=f"Linked Discord account {active_discord} was matched with credit '{raw}' in the video's contributor information."
                )

    # 5. Attempt Instagram Match
    if active_ig and extracted_ig:
        active_ig_norm = normalize_for_comparison(active_ig)
        matched_ig = None
        for acc in extracted_ig:
            if acc.lower() == active_ig.lower() or normalize_for_comparison(acc) == active_ig_norm:
                matched_ig = acc
                break

        if matched_ig:
            return AutoVerificationResult(
                verified=True,
                status="auto_verified",
                method="youtube_description_instagram_match",
                matched_account=active_ig,
                linked_account=active_ig,
                extracted_accounts=extracted_combined,
                reason=f"Linked Instagram account @{active_ig} was matched with credit '{matched_ig}' in the video's contributor information."
            )

    # 6. If no accounts/credits were found at all
    if not extracted_combined:
        primary_linked = active_ig or active_discord
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_instagram" if active_ig else "fallback_no_match",
            method=None,
            matched_account=None,
            linked_account=primary_linked,
            extracted_accounts=[],
            reason="No contributor credits detected in the video description. Continuing to existing verification."
        )

    # 7. Credits were found, but none matched the linked accounts
    primary_linked = active_ig or active_discord
    preview_list = [f"@{acc}" if (" " not in acc and not acc.isdigit()) else f'"{acc}"' for acc in extracted_combined[:3]]
    accounts_preview = ", ".join(preview_list)
    if len(extracted_combined) > 3:
        accounts_preview += f" (+{len(extracted_combined) - 3} more)"

    display_linked = f"@{active_ig}" if active_ig else f"Discord ID {active_discord}"
    return AutoVerificationResult(
        verified=False,
        status="fallback_no_match",
        method=None,
        matched_account=None,
        linked_account=primary_linked,
        extracted_accounts=extracted_combined,
        reason=f"Detected contributor credit(s) {accounts_preview}, but none match your linked account ({display_linked}). Continuing to existing verification."
    )


async def verify_contribution_from_description_async(
    description: Optional[str],
    linked_account: Optional[str] = None,
    linked_discord_account: Optional[str] = None,
    user_role: Optional[str] = None
) -> AutoVerificationResult:
    """Async verification that strictly verifies candidate existence on social platforms before matching."""
    if not description or not description.strip():
        return verify_contribution_from_description(
            description,
            linked_account=linked_account,
            linked_discord_account=linked_discord_account,
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
        if ("Instagram" in c.get("platforms", []) or c.get("is_name") or c.get("platforms")) and c.get("username")
    ]
    return verify_contribution_from_description(
        description,
        linked_account=linked_account,
        linked_discord_account=linked_discord_account,
        user_role=user_role,
        verified_accounts=verified_handles
    )


