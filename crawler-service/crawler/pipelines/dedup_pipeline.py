import hashlib
import redis
from scrapy.exceptions import DropItem


class DeduplicationPipeline:
    """
    Before anything hits Postgres, check Redis for a dedup hash.
    Key format: dedup:{md5(company::role)}
    TTL: 7 days — a job reposted after a week is worth seeing again.
    """

    TTL_SECONDS = 60 * 60 * 24 * 7

    def open_spider(self, spider):
        self.redis = redis.Redis(
            host=spider.settings.get("REDIS_HOST", "localhost"),
            port=spider.settings.getint("REDIS_PORT", 6379),
            decode_responses=True,
        )
        spider.logger.info("DeduplicationPipeline connected to Redis")

    def process_item(self, item, spider):
        key = self._make_key(item)

        if self.redis.exists(key):
            raise DropItem(f"Duplicate skipped: {item.get('company')} / {item.get('role')}")

        self.redis.setex(key, self.TTL_SECONDS, "1")
        return item

    def _make_key(self, item) -> str:
        company = (item.get("company") or "").lower().strip()
        role = (item.get("role") or "").lower().strip()
        raw = f"{company}::{role}"
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"dedup:{digest}"
