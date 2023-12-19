import asyncio
import logging

from scrapy import Request, Spider
from scrapy_playwright.handler import ScrapyPlaywrightDownloadHandler
from playwright_stealth import stealth_async
from scrapy.utils.defer import deferred_from_coro


# working on Windows ######################################
import sys

from twisted.internet.defer import Deferred, inlineCallbacks

if sys.platform == 'win32' and sys.version_info >= (3, 8):
    import threading

    _loop = None
    _thread = None


    def get_default_event_loop():
        global _loop, _thread
        if _thread is None:
            if _loop is None:
                _loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()
                asyncio.set_event_loop(_loop)
            if not _loop.is_running():
                _thread = threading.Thread(
                    target=_loop.run_forever,
                    daemon=True)
                _thread.start()
        return _loop


    deferred_from_coro__old = deferred_from_coro


    def deferred_from_coro(o):
        async def get_result():
            future = asyncio.run_coroutine_threadsafe(o, get_default_event_loop())
            result = future.result()
            return result

        if isinstance(o, Deferred):
            return o
        return deferred_from_coro__old(get_result())
# working on Windows ######################################

logger = logging.getLogger("scrapy-playwright")


class StealthScrapyPlaywrightDownloadHandler(ScrapyPlaywrightDownloadHandler):

    async def _create_page(self, request, spider):
        page = await super(StealthScrapyPlaywrightDownloadHandler, self)._create_page(request, spider)
        await stealth_async(page)
        return page

    def _engine_started(self) -> Deferred:
        """Launch the browser. Use the engine_started signal as it supports returning deferreds."""
        return deferred_from_coro(self._launch())

    @inlineCallbacks
    def close(self) -> Deferred:
        logger.info("Closing download handler")
        yield super().close()
        yield deferred_from_coro(self._close())

    def download_request(self, request: Request, spider: Spider) -> Deferred:
        if request.meta.get("playwright"):
            return deferred_from_coro(self._download_request(request, spider))
        return super().download_request(request, spider)
