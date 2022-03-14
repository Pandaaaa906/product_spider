from scrapy.utils.reactor import install_reactor, is_asyncio_reactor_installed

install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")
is_asyncio_reactor_installed = is_asyncio_reactor_installed()
print(f"Is asyncio reactor installed: {is_asyncio_reactor_installed}")
from scrapyd.runner import main  # noqa: E402 needs after install reactor

if __name__ == "__main__":
    main()
