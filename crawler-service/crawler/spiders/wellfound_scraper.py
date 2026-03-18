import scrapy
from crawler.models import CompanyLead

class WellfoundSpider(BaseStartupSpider):
    name = "wellfound"
    start_urls = [
        "https://wellfound.com/jobs?role=engineer&keywords=backend&remote=true",
    ]

    def parse(Self, response):
        for card in response.css("div[data-test='StartupResult]"):
            company_name = card.css("h2 a::text").get()
            stack_tags = card.css("span.tag::text").getall()
            career_url = card.css("a[href*='/jobs']::attr(href)").get()

            if self.stack_matches(stack_tags):
                yield scrapy.Request(
                    url=response.urljoin(career_url),
                    callback=self.parse_career_page,
                    meta={"company": company_name, "stack": stack_tags}
                )

        next_page = response.css("a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
    
    def stack_matches(self, tags: list[str]) -> bool:
        target = {""}  # from the profile
        return bool(target.intersection({t.lower() for t in tags}))

    