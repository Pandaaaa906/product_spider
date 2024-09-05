from scrapy_playwright.handler import ScrapyPlaywrightDownloadHandler
from playwright_stealth import stealth_async


class StealthScrapyPlaywrightDownloadHandler(ScrapyPlaywrightDownloadHandler):

    async def _create_page(self, request, spider):
        page = await super(StealthScrapyPlaywrightDownloadHandler, self)._create_page(request, spider)
        await stealth_async(page)
        return page
