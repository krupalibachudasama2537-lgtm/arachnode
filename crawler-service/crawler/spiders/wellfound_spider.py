import scrapy
from scrapy_playwright.page import PageMethod
from crawler.spiders.base_spider import BaseStartupSpider
from crawler.models import JobItem


class WellfoundSpider(BaseStartupSpider):
    """
    Crawls wellfound.com (formerly AngelList Talent) for startup job listings.
    Requires Playwright because the page is a React SPA.

    Rate-limit note: wellfound is aggressive about bot detection.
    Keep DOWNLOAD_DELAY >= 3 and never run this in parallel with other spiders.
    """
    name = "wellfound"

    def start_requests(self):
        role_slug = self.settings.get("JOBSEEKER_ROLE", "engineer").lower().replace(" ", "-")
        url = f"https://wellfound.com/jobs?role={role_slug}"

        yield scrapy.Request(
            url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "div[data-test='StartupResult']", timeout=15000),
                ],
            },
            callback=self.parse,
            errback=self.handle_error,
        )

    async def parse(self, response):
        page = response.meta.get("playwright_page")

        for card in response.css("div[data-test='StartupResult']"):
            company = card.css("h2 a::text, h3 a::text").get("").strip()
            stack_tags = card.css("span.tag::text, div[class*='tag']::text").getall()
            product_desc = card.css("p[class*='description']::text").get("").strip()

            # Only follow companies whose stack overlaps ours
            if not self.stack_matches(stack_tags):
                continue

            jobs_link = card.css("a[href*='/jobs']::attr(href)").get()
            if not jobs_link:
                continue

            yield response.follow(
                jobs_link,
                callback=self.parse_company_jobs,
                meta={
                    "company": company,
                    "stack": stack_tags,
                    "product": product_desc,
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                },
                errback=self.handle_error,
            )

        # Pagination — Wellfound uses a "Load more" button, not a next-page link
        if page:
            load_more = await page.query_selector("button[data-test='load-more']")
            if load_more:
                await load_more.click()
                await page.wait_for_selector("div[data-test='StartupResult']")
                new_content = await page.content()
                yield scrapy.Request(
                    response.url,
                    callback=self.parse,
                    meta=response.meta,
                    dont_filter=True,
                )
            await page.close()

    def parse_company_jobs(self, response):
        company = response.meta["company"]
        stack = response.meta["stack"]
        product = response.meta["product"]

        for job_row in response.css("div[data-test='job-listing'], li[class*='job']"):
            role_text = job_row.css("h2::text, h3::text, a::text").get("").strip()
            role_url = job_row.css("a::attr(href)").get("")
            location = job_row.css("span[class*='location']::text").get("").strip()

            if not role_text or not self.role_matches(role_text):
                continue

            yield JobItem(
                company=company,
                role=role_text,
                source=self.name,
                url=response.urljoin(role_url) if role_url else response.url,
                stack=stack,
                product=product,
                location=location,
                posted_at=None,
            )

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure.request.url} — {failure.value}")
