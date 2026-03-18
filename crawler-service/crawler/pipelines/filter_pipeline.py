from scrapy.exceptions import DropItem


class StackFilterPipeline:
    """
    Secondary filter after dedup. Drops any item whose stack has zero overlap
    with the target stack. This catches cases where the spider emitted an item
    before stack-matching was possible (e.g. after following a career page link).

    If JOBSEEKER_STACK is empty, every item passes through.
    """

    def open_spider(self, spider):
        raw = spider.settings.get("JOBSEEKER_STACK", "")
        self.target_stack = {s.strip().lower() for s in raw.split(",") if s.strip()}
        spider.logger.info(f"StackFilterPipeline target: {self.target_stack or 'any'}")

    def process_item(self, item, spider):
        if not self.target_stack:
            return item

        item_stack = {t.strip().lower() for t in (item.get("stack") or [])}

        # Also check the role title for stack hints (e.g. "Python Backend Engineer")
        role_text = (item.get("role") or "").lower()
        role_tokens = set(role_text.split())

        combined = item_stack | role_tokens

        if not self.target_stack.intersection(combined):
            raise DropItem(
                f"Stack mismatch: {item.get('company')} / {item.get('role')} "
                f"(item_stack={item_stack})"
            )

        return item
