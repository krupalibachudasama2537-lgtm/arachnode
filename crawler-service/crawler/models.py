from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import scrapy


@dataclass
class JobPosting:
    company: str
    role: str
    source: str
    url: str
    stack: list[str] = field(default_factory=list)
    product: str = ""
    location: str = ""
    posted_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "role": self.role,
            "source": self.source,
            "url": self.url,
            "stack": self.stack,
            "product": self.product,
            "location": self.location,
            "posted_at": self.posted_at or datetime.utcnow().isoformat(),
        }


class JobItem(scrapy.Item):
    """Scrapy Item wrapper around JobPosting fields."""
    company = scrapy.Field()
    role = scrapy.Field()
    source = scrapy.Field()
    url = scrapy.Field()
    stack = scrapy.Field()
    product = scrapy.Field()
    location = scrapy.Field()
    posted_at = scrapy.Field()
