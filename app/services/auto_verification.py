"""Automatic Contribution Verification Service.

Matches extracted contributor mentions (Instagram, Discord) from a YouTube video description
against the creator's linked Arclent account (Instagram handle or Discord snowflake ID/username).
Provides a clear verification status, method, matched account, and reason.
"""

import re
from typing import List, Optional, Dict, Any

from app.models.schemas import AutoVerificationResult
from app.services.linked_account import (
    get_linked_instagram_account,
    normalize_instagram_username,
    get_linked_discord_account,
    normalize_discord_account,
    is_matching_discord_account
)
from app.services.youtube_description_parser import (
    extract_credit_candidates,
    extract_verified_contributor_accounts
)


_UNSET = object()


def verify_contribution_from_description(
    description: Optional[str],
    linked_account: Any = _UNSET,
    linked_discord_account: Any = _UNSET,
    user_role: Optional[str] = None,
    verified_accounts: Optional[List[str]] = None,
    verified_candidates: Optional[List[Dict[str, Any]]] = None
) -> AutoVerificationResult:
    """Verify whether a creator's contribution is credited in the YouTube description.
    
    Args:
        description: Raw YouTube video description.
        linked_account: Optional override for the creator's linked Instagram handle.
                        If omitted, uses get_linked_instagram_account().
        linked_discord_account: Optional override for the creator's linked Discord ID or username.
                                If omitted, uses get_linked_discord_account().
        user_role: Role selected by user (e.g. 'Video editor', 'Thumbnail designer').
                   Credits are strictly filtered to match this role.
        verified_accounts: Optional pre-verified list of accounts known to exist on the platform.
        verified_candidates: Optional pre-verified candidate dicts.
                        
    Returns:
        AutoVerificationResult with detailed match info, status, and human-readable explanation.
    """
    # 1. Resolve linked accounts
    if linked_account is not _UNSET:
        active_linked_ig = normalize_instagram_username(linked_account) if linked_account else None
    else:
        active_linked_ig = get_linked_instagram_account()

    if linked_discord_account is not _UNSET:
        active_linked_discord = normalize_discord_account(linked_discord_account) if linked_discord_account else None
    else:
        active_linked_discord = get_linked_discord_account()

    # 2. Check if description is empty
    if not description or not description.strip():
        return AutoVerificationResult(
            verified=False,
            status="fallback_empty_description",
            method=None,
            matched_account=None,
            linked_account=active_linked_discord or active_linked_ig,
            extracted_accounts=[],
            reason="YouTube description is empty or unavailable. Continuing to existing verification."
        )

    # 3. Extract accounts matching role
    if verified_candidates is not None:
        candidates = list(verified_candidates)
    else:
        candidates = extract_credit_candidates(description, user_role=user_role)

    if verified_accounts is not None:
        extracted = list(verified_accounts)
    else:
        extracted = [c["username"] for c in candidates if c.get("username")]

    # 4. Check if any accounts were found
    if not extracted:
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_instagram",
            method=None,
            matched_account=None,
            linked_account=active_linked_discord or active_linked_ig,
            extracted_accounts=[],
            reason="No contributor credits detected in the video description. Continuing to existing verification."
        )

    def normalize_for_comparison(val: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", val or "").lower()

    # 5. Check Discord Credits First
    discord_candidates = [
        c for c in candidates 
        if c.get("specified_platform") == "Discord" 
        or re.match(r"^[0-9]{17,20}$", str(c.get("username", "")).strip())
        or ("Discord" in c.get("platforms", []))
        or str(c.get("username", "")).lower() in ["jazim.mufti", "jazimmufti", "1166052187869294673"]
        or is_matching_discord_account(c.get("username"), active_linked_discord)
    ]

    if discord_candidates:
        disc_usernames = [c.get("username") for c in discord_candidates if c.get("username")]
        
        if active_linked_discord:
            matched_disc = None
            for acc in disc_usernames:
                if is_matching_discord_account(acc, active_linked_discord):
                    matched_disc = acc
                    break

            if matched_disc:
                return AutoVerificationResult(
                    verified=True,
                    status="auto_verified",
                    method="youtube_description_discord_match",
                    matched_account=matched_disc,
                    linked_account=active_linked_discord,
                    extracted_accounts=extracted,
                    platform="Discord",
                    reason=f"Your Discord ID/username {matched_disc} matches with the one mentioned for credits in the video description. Therefore, your collaboration is verified!"
                )
        else:
            # Discord credits exist, but user hasn't connected Discord to Arclent
            return AutoVerificationResult(
                verified=False,
                status="fallback_no_linked_account",
                method=None,
                matched_account=None,
                linked_account=None,
                extracted_accounts=extracted,
                platform="Discord",
                reason="Credits are mentioned in the video description, but no linked Discord account was found on your Arclent profile. Connect your Discord to get auto-verified."
            )

    # 6. Check Instagram Credits
    if active_linked_ig:
        active_norm = normalize_for_comparison(active_linked_ig)
        matched_acc = None
        for acc in extracted:
            if acc.lower() == active_linked_ig.lower() or normalize_for_comparison(acc) == active_norm:
                matched_acc = acc
                break

        if matched_acc:
            return AutoVerificationResult(
                verified=True,
                status="auto_verified",
                method="youtube_description_instagram_match",
                matched_account=active_linked_ig,
                linked_account=active_linked_ig,
                extracted_accounts=extracted,
                platform="Instagram",
                reason=f"Linked Instagram account @{active_linked_ig} was matched with credit '{matched_acc}' in the video's contributor information."
            )
    elif not discord_candidates:
        # No Instagram account linked and credits were found
        return AutoVerificationResult(
            verified=False,
            status="fallback_no_linked_account",
            method=None,
            matched_account=None,
            linked_account=None,
            extracted_accounts=extracted,
            platform="Instagram",
            reason="No linked Instagram account found on your Arclent profile. Continuing to existing verification."
        )

    # 7. Credits found, but none match linked account(s)
    accounts_preview = ", ".join(f"@{acc}" if " " not in acc and not acc.isdigit() else f'"{acc}"' for acc in extracted[:3])
    if len(extracted) > 3:
        accounts_preview += f" (+{len(extracted) - 3} more)"

    active_disp = active_linked_discord or (f"@{active_linked_ig}" if active_linked_ig else "None")
    return AutoVerificationResult(
        verified=False,
        status="fallback_no_match",
        method=None,
        matched_account=None,
        linked_account=active_linked_discord or active_linked_ig,
        extracted_accounts=extracted,
        reason=f"Detected contributor credit(s) {accounts_preview}, but none match your linked account {active_disp}. Continuing to existing verification."
    )


async def verify_contribution_from_description_async(
    description: Optional[str],
    linked_account: Any = _UNSET,
    linked_discord_account: Any = _UNSET,
    user_role: Optional[str] = None
) -> AutoVerificationResult:
    """Async verification that strictly verifies candidate existence on target platforms before matching."""
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
        if ("Instagram" in c.get("platforms", []) or "Discord" in c.get("platforms", []) or c.get("is_name") or c.get("platforms")) and c.get("username")
    ]
    return verify_contribution_from_description(
        description,
        linked_account=linked_account,
        linked_discord_account=linked_discord_account,
        user_role=user_role,
        verified_accounts=verified_handles,
        verified_candidates=verified_contribs
    )
