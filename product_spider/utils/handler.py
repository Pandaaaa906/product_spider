from scrapy_playwright.handler import ScrapyPlaywrightDownloadHandler
from playwright_stealth import stealth_async


class StealthScrapyPlaywrightDownloadHandler(ScrapyPlaywrightDownloadHandler):

    async def _create_page(self, request):
        page = await super(StealthScrapyPlaywrightDownloadHandler, self)._create_page(request)
        await stealth_async(page)
        return page
