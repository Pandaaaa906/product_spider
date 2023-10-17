import scrapyautodb as scrapy


class RawSupplier(scrapy.OrderedItem):
    source = scrapy.Field()
    name = scrapy.Field()
    en_name = scrapy.Field()
    region = scrapy.Field()
    website = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    attrs = scrapy.Field()

    class Meta:
        indexes = (
            (("source", "name",), True),
        )
