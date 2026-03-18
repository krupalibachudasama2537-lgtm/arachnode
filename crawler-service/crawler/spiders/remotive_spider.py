import json
import scrapy
from crawler.spiders.base_spider import BaseStartupSpider
from crawler.models import JobItem


class RemotiveSpider(BaseStartupSpider):
    """
    Remotive exposes a free public JSON API — no scraping needed at all.
    https://remotive.com/api/remote-jobs

    This is the most reliable spider to start with when testing your pipeline
    end-to-end since it never breaks due to HTML changes.
    """
    name = "remotive"
    API_URL = "https://remotive.com/api/remote-jobs?category=software-dev&limit=100"

    def start_requests(self):
        yield scrapy.Request(self.API_URL, callback=self.parse_json)

    def parse_json(self, response):
        try:
            data = response.json()
        except Exception:
            self.logger.error("Failed to parse Remotive API response as JSON")
            return

        jobs = data.get("jobs", [])
        self.logger.info(f"Remotive: {len(jobs)} raw jobs fetched")

        for job in jobs:
            company = job.get("company_name", "")
            role_text = job.get("title", "")
            tags = job.get("tags", [])          # list of strings like ["python", "django"]
            stack_tags = [t for t in tags if isinstance(t, str)]

            if not self.role_matches(role_text):
                continue

            if not self.stack_matches(stack_tags):
                continue

            yield JobItem(
                company=company,
                role=role_text,
                source=self.name,
                url=job.get("url", ""),
                stack=stack_tags,
                product=job.get("company_description", "")[:300],
                location=job.get("candidate_required_location", "Remote"),
                posted_at=job.get("publication_date"),
            )

    # Remotive has no pagination on the free API — limit=100 is the ceiling.
    # For more results, filter by different categories and run multiple requests.
    def parse(self, response):
        pass
