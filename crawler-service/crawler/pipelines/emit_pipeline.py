import json
import redis
from datetime import datetime, timezone


class RedisStreamPipeline:
    """
    Final pipeline stage. Pushes each passing item as an event onto
    the 'jobs:raw' Redis Stream so the Aggregator service can consume it.

    Stream is capped at 10,000 entries (maxlen) to avoid unbounded growth
    on a personal machine.
    """

    STREAM_KEY = "jobs:raw"
    MAX_STREAM_LENGTH = 10_000

    def open_spider(self, spider):
        self.redis = redis.Redis(
            host=spider.settings.get("REDIS_HOST", "localhost"),
            port=spider.settings.getint("REDIS_PORT", 6379),
            decode_responses=True,
        )
        self.emitted = 0
        spider.logger.info(f"RedisStreamPipeline ready → stream '{self.STREAM_KEY}'")

    def close_spider(self, spider):
        spider.logger.info(f"RedisStreamPipeline: emitted {self.emitted} events this run")

    def process_item(self, item, spider):
        # Redis Streams only accept flat string values — serialise lists to JSON
        payload = {
            "company":    str(item.get("company") or ""),
            "role":       str(item.get("role") or ""),
            "source":     str(item.get("source") or spider.name),
            "url":        str(item.get("url") or ""),
            "stack":      json.dumps(item.get("stack") or []),
            "product":    str(item.get("product") or ""),
            "location":   str(item.get("location") or ""),
            "posted_at":  str(
                item.get("posted_at") or
                datetime.now(tz=timezone.utc).isoformat()
            ),
        }

        self.redis.xadd(
            self.STREAM_KEY,
            payload,
            maxlen=self.MAX_STREAM_LENGTH,
            approximate=True,
        )
        self.emitted += 1

        spider.logger.debug(
            f"Emitted → {payload['company']} / {payload['role']} [{payload['source']}]"
        )
        return item
