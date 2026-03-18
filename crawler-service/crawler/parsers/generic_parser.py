"""
Generic career page parser for companies that don't use a known ATS.
Uses Playwright to render JavaScript-heavy pages and extract job listings
using broad CSS selectors that work across most career page layouts.
"""
import asyncio
from typing import Optional


async def parse_generic_career_page(url: str) -> list[dict]:
    """
    Render the page with Playwright and extract job listings using
    heuristic selectors. Works for most custom React/Next.js career pages.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[generic_parser] playwright not installed — skipping")
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=20_000)
        except Exception as e:
            print(f"[generic_parser] Navigation failed for {url}: {e}")
            await browser.close()
            return []

        jobs = []

        # Strategy 1: look for common job listing container patterns
        SELECTORS = [
            "li:has(a[href*='job'])",
            "li:has(a[href*='career'])",
            "div[class*='job-listing']",
            "div[class*='position']",
            "div[class*='opening']",
            "article[class*='job']",
            "tr:has(a[href*='job'])",
        ]

        found_elements = []
        for selector in SELECTORS:
            try:
                els = await page.query_selector_all(selector)
                if els:
                    found_elements = els
                    break
            except Exception:
                continue

        for el in found_elements[:30]:     # cap at 30 per page
            try:
                text = (await el.inner_text()).strip()
                if not text or len(text) > 200 or len(text) < 5:
                    continue

                link_el = await el.query_selector("a[href]")
                href = await link_el.get_attribute("href") if link_el else None

                # Resolve relative URLs
                if href and href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)

                jobs.append({
                    "role": text.split("\n")[0].strip(),     # first line is usually the title
                    "url": href or url,
                    "location": _extract_location(text),
                    "posted_at": None,
                    "tags": [],
                })
            except Exception:
                continue

        await browser.close()
        return jobs


def _extract_location(text: str) -> str:
    """
    Very rough heuristic to pull a location hint from job text.
    Most career pages include 'Remote', 'Bangalore', 'San Francisco' etc.
    """
    keywords = [
        "remote", "bangalore", "bengaluru", "mumbai", "delhi",
        "hyderabad", "pune", "chennai", "san francisco", "new york",
        "london", "berlin", "singapore", "worldwide",
    ]
    lower = text.lower()
    for kw in keywords:
        if kw in lower:
            return kw.title()
    return ""


if __name__ == "__main__":
    # Quick manual test
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com/jobs"
    results = asyncio.run(parse_generic_career_page(url))
    for r in results:
        print(r)
