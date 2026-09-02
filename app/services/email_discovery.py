"""Email discovery and verification service."""

import re
import logging
from typing import List, Optional, Set
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from app.models.schemas import EmailCandidate

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", 
    re.IGNORECASE
)

OBFUSCATED_PATTERNS = [
    re.compile(r"([A-Za-z0-9._%+-]+)\s*(?:\[at\]|\(at\)|\sat\s|@)\s*([A-Za-z0-9.-]+)\s*(?:\[dot\]|\(dot\)|\sdot\s|\.)\s*([A-Za-z]{2,})", re.IGNORECASE),
]

EXCLUDED_DOMAINS = {
    "youtube.com", "google.com", "gstatic.com", "googleapis.com", 
    "facebook.com", "instagram.com", "twitter.com", "x.com", 
    "tiktok.com", "github.com", "apple.com", "w3.org", "schema.org",
    "sentry.io", "cloudflare.com", "example.com", "domain.com",
    "email.com", "test.com", "tempmail.com"
}

EXCLUDED_PREFIXES = {
    "noreply", "no-reply", "donotreply", "mailer-daemon", "support", 
    "security", "abuse", "privacy", "terms", "admin", "postmaster"
}

INVALID_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".css", ".js", ".json"
)


def clean_email(email_str: str) -> Optional[str]:
    """Clean and validate an extracted email string."""
    if not email_str:
        return None
    
    email_str = email_str.strip().lower().rstrip(".,;)>\"'").lstrip("(<\"'")
    
    if any(email_str.endswith(ext) for ext in INVALID_EXTENSIONS):
        return None
        
    if "@" not in email_str:
        return None
        
    parts = email_str.split("@")
    if len(parts) != 2:
        return None
        
    user, domain = parts
    if not user or not domain:
        return None
        
    if domain in EXCLUDED_DOMAINS:
        return None
        
    if user in EXCLUDED_PREFIXES:
        return None
        
    if len(domain.split(".")) < 2:
        return None

    return email_str


def extract_context_snippet(text: str, email: str, window: int = 60) -> str:
    """Extract a small snippet of text surrounding the discovered email for attribution."""
    idx = text.lower().find(email.lower())
    if idx == -1:
        return "Discovered in public text content."
    start = max(0, idx - window)
    end = min(len(text), idx + len(email) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


def extract_emails_from_text(text: str, source_label: str = "YouTube video description") -> List[EmailCandidate]:
    """Extract public emails from text content using regex and pattern matching."""
    if not text:
        return []

    candidates: List[EmailCandidate] = []
    seen: Set[str] = set()

    # 1. Standard regex matches
    matches = EMAIL_REGEX.findall(text)
    for raw in matches:
        cleaned = clean_email(raw)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            
            # Determine confidence
            lower_text = text.lower()
            is_business = any(k in lower_text for k in ["business", "inquiries", "booking", "contact", "mgmt", "management", "sponsor", "press", "pr"])
            confidence = "high" if is_business else "medium"
            
            candidates.append(
                EmailCandidate(
                    email=cleaned,
                    source=source_label,
                    source_type="publicly_published",
                    confidence=confidence,
                    context=extract_context_snippet(text, raw)
                )
            )

    # 2. Obfuscated matches (e.g. john [at] domain [dot] com)
    for ob_pat in OBFUSCATED_PATTERNS:
        for match in ob_pat.finditer(text):
            reconstructed = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            cleaned = clean_email(reconstructed)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                candidates.append(
                    EmailCandidate(
                        email=cleaned,
                        source=f"{source_label} (obfuscated format)",
                        source_type="publicly_published",
                        confidence="high",
                        context=extract_context_snippet(text, match.group(0))
                    )
                )

    return candidates


async def crawl_website_for_emails(website_url: str) -> List[EmailCandidate]:
    """Respectfully crawl a creator's official website contact/about pages to find public email."""
    if not website_url:
        return []

    candidates: List[EmailCandidate] = []
    seen: Set[str] = set()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        parsed_base = urlparse(website_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        target_urls = [
            website_url,
            urljoin(base_domain, "/contact"),
            urljoin(base_domain, "/about"),
            urljoin(base_domain, "/contact-us"),
            urljoin(base_domain, "/press")
        ]

        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True, headers=headers) as client:
            for url in target_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                        soup = BeautifulSoup(resp.text, "html.parser")
                        
                        # 1. Search mailto: links
                        for mailto in soup.select('a[href^="mailto:"]'):
                            href = mailto.get("href", "")
                            raw_email = href.replace("mailto:", "").split("?")[0].strip()
                            cleaned = clean_email(raw_email)
                            if cleaned and cleaned not in seen:
                                seen.add(cleaned)
                                candidates.append(
                                    EmailCandidate(
                                        email=cleaned,
                                        source=f"Creator website ({url})",
                                        source_type="publicly_published",
                                        confidence="high",
                                        context=f"Published 'mailto:' contact link on {url}"
                                    )
                                )

                        # 2. Search body text
                        page_text = soup.get_text(separator=" ", strip=True)
                        page_emails = extract_emails_from_text(page_text, source_label=f"Creator website ({url})")
                        for cand in page_emails:
                            if cand.email not in seen:
                                seen.add(cand.email)
                                candidates.append(cand)
                                
                    if len(candidates) >= 3:
                        break
                except Exception as e:
                    logger.debug(f"Could not scrape {url}: {e}")
                    continue

    except Exception as e:
        logger.warning(f"Error during website email crawl for {website_url}: {e}")

    return candidates
