"""
tests/test_ats_detector.py

Run with: pytest tests/ -v
No external network calls — all ATS detection logic is pure functions.
"""
import pytest
from crawler.parsers.ats_detector import detect_ats, extract_company_slug, fetch_ats_jobs


# ── ATS detection ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://jobs.lever.co/stripe/abc123",          "lever"),
    ("https://jobs.lever.co/razorpay",               "lever"),
    ("https://boards.greenhouse.io/notion/jobs/123", "greenhouse"),
    ("https://grnh.se/abc123",                       "greenhouse"),
    ("https://jobs.ashbyhq.com/linear",              "ashby"),
    ("https://myworkdayjobs.com/atlassian/job/1",    "workday"),
    ("https://careers.stripe.com/jobs/123",          "generic"),
    ("https://stripe.com/jobs",                      "generic"),
])
def test_detect_ats(url, expected):
    assert detect_ats(url) == expected


# ── Slug extraction ────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,ats,expected_slug", [
    ("https://jobs.lever.co/stripe/abc123",          "lever",      "stripe"),
    ("https://boards.greenhouse.io/notion/jobs/123", "greenhouse", "notion"),
    ("https://jobs.ashbyhq.com/linear",              "ashby",      "linear"),
    ("https://careers.stripe.com/jobs",              "generic",    None),
])
def test_extract_slug(url, ats, expected_slug):
    assert extract_company_slug(url, ats) == expected_slug


# ── Dedup key stability ────────────────────────────────────────────────────

def test_dedup_key_is_stable():
    """Same company/role should always produce the same hash key."""
    import hashlib
    from crawler.pipelines.dedup_pipeline import DeduplicationPipeline

    pipeline = DeduplicationPipeline()
    # We can't call open_spider without a real spider, so test the key method directly
    item = {"company": "Razorpay", "role": "Backend Engineer"}
    key1 = pipeline._make_key(item)
    key2 = pipeline._make_key(item)
    assert key1 == key2
    assert key1.startswith("dedup:")


def test_dedup_key_is_case_insensitive():
    from crawler.pipelines.dedup_pipeline import DeduplicationPipeline
    pipeline = DeduplicationPipeline()

    item_lower = {"company": "razorpay", "role": "backend engineer"}
    item_upper = {"company": "RAZORPAY", "role": "Backend Engineer"}
    assert pipeline._make_key(item_lower) == pipeline._make_key(item_upper)


# ── Stack filter ───────────────────────────────────────────────────────────

class FakeSpider:
    class settings:
        @staticmethod
        def get(key, default=""):
            return {"JOBSEEKER_STACK": "python,go,kubernetes"}.get(key, default)
    logger = type("L", (), {"info": lambda *a: None})()


def test_stack_filter_passes_matching_item():
    from crawler.pipelines.filter_pipeline import StackFilterPipeline
    from scrapy.exceptions import DropItem

    pipeline = StackFilterPipeline()
    pipeline.open_spider(FakeSpider())

    item = {"company": "Zepto", "role": "Backend Engineer", "stack": ["Python", "FastAPI"]}
    result = pipeline.process_item(item, FakeSpider())
    assert result == item


def test_stack_filter_drops_non_matching_item():
    from crawler.pipelines.filter_pipeline import StackFilterPipeline
    from scrapy.exceptions import DropItem

    pipeline = StackFilterPipeline()
    pipeline.open_spider(FakeSpider())

    item = {"company": "SomeJavaShop", "role": "Java Developer", "stack": ["Java", "Spring"]}
    with pytest.raises(DropItem):
        pipeline.process_item(item, FakeSpider())
