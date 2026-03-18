"""
ATS (Applicant Tracking System) detection and structured parsing.

Lever and Greenhouse expose public JSON APIs for job listings.
This means for any company using these systems, we get clean structured
data with zero HTML scraping.
"""
import httpx
from typing import Optional


# ── Detection ──────────────────────────────────────────────────────────────

ATS_PATTERNS: dict[str, callable] = {
    "lever":      lambda url: "jobs.lever.co" in url,
    "greenhouse": lambda url: "boards.greenhouse.io" in url or "grnh.se" in url,
    "ashby":      lambda url: "jobs.ashbyhq.com" in url,
    "workday":    lambda url: "myworkdayjobs.com" in url,
}


def detect_ats(url: str) -> str:
    for name, matcher in ATS_PATTERNS.items():
        if matcher(url):
            return name
    return "generic"


def extract_company_slug(url: str, ats: str) -> Optional[str]:
    """
    Pull the company identifier from a known ATS URL.
    e.g. https://jobs.lever.co/stripe/abc -> 'stripe'
    """
    try:
        from urllib.parse import urlparse
        parts = urlparse(url).path.strip("/").split("/")
        if ats in ("lever", "greenhouse", "ashby") and parts:
            return parts[0]
    except Exception:
        pass
    return None


# ── Lever ──────────────────────────────────────────────────────────────────

def fetch_lever_jobs(company_slug: str) -> list[dict]:
    """
    Lever's public API: https://api.lever.co/v0/postings/{company}?mode=json
    Returns a list of open roles as clean JSON — no auth required.
    """
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        postings = resp.json()
    except Exception as e:
        print(f"[lever] Failed for {company_slug}: {e}")
        return []

    results = []
    for job in postings:
        categories = job.get("categories", {})
        results.append({
            "role":     job.get("text", ""),
            "team":     categories.get("team", ""),
            "location": categories.get("location", ""),
            "url":      job.get("hostedUrl", ""),
            "posted_at": _ms_to_iso(job.get("createdAt")),
            "tags":     job.get("tags", []),
        })
    return results


# ── Greenhouse ─────────────────────────────────────────────────────────────

def fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """
    Greenhouse public API: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
    Also requires no auth for public job boards.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[greenhouse] Failed for {company_slug}: {e}")
        return []

    results = []
    for job in data.get("jobs", []):
        location = job.get("location", {}).get("name", "")
        results.append({
            "role":     job.get("title", ""),
            "team":     job.get("departments", [{}])[0].get("name", "") if job.get("departments") else "",
            "location": location,
            "url":      job.get("absolute_url", ""),
            "posted_at": job.get("updated_at"),
            "tags":     [],
        })
    return results


# ── Ashby ──────────────────────────────────────────────────────────────────

def fetch_ashby_jobs(company_slug: str) -> list[dict]:
    """
    Ashby also has a public JSON endpoint — less documented but consistent.
    """
    url = f"https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
    payload = {
        "operationName": "ApiJobBoardWithTeams",
        "variables": {"organizationHostedJobsPageName": company_slug},
        "query": """
          query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
            jobBoard: jobBoardWithTeams(
              organizationHostedJobsPageName: $organizationHostedJobsPageName
            ) {
              jobPostings { id title locationName jobPostingState isRemote externalLink }
            }
          }
        """,
    }
    try:
        resp = httpx.post(url, json=payload, timeout=10)
        data = resp.json()
        postings = (
            data.get("data", {})
                .get("jobBoard", {})
                .get("jobPostings", [])
        )
    except Exception as e:
        print(f"[ashby] Failed for {company_slug}: {e}")
        return []

    return [
        {
            "role":     p.get("title", ""),
            "location": p.get("locationName", "Remote" if p.get("isRemote") else ""),
            "url":      p.get("externalLink", f"https://jobs.ashbyhq.com/{company_slug}/{p.get('id')}"),
            "posted_at": None,
            "tags":     [],
        }
        for p in postings
        if p.get("jobPostingState") == "Published"
    ]


# ── Unified entry point ────────────────────────────────────────────────────

def fetch_ats_jobs(career_url: str) -> list[dict]:
    """
    Given any career page URL, auto-detect the ATS and return structured jobs.
    Returns an empty list if the ATS is unknown (caller should use generic parser).
    """
    ats = detect_ats(career_url)
    slug = extract_company_slug(career_url, ats)

    if not slug:
        return []

    if ats == "lever":
        return fetch_lever_jobs(slug)
    if ats == "greenhouse":
        return fetch_greenhouse_jobs(slug)
    if ats == "ashby":
        return fetch_ashby_jobs(slug)

    return []   # generic fallback — caller handles Playwright


# ── Helpers ────────────────────────────────────────────────────────────────

def _ms_to_iso(ms_timestamp) -> Optional[str]:
    if not ms_timestamp:
        return None
    from datetime import datetime, timezone
    try:
        dt = datetime.fromtimestamp(int(ms_timestamp) / 1000, tz=timezone.utc)
        return dt.isoformat()
    except Exception:
        return None
