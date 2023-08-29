import scrapyautodb as scrapy


class SooPATPatent(scrapy.OrderedItem):
    code = scrapy.Field()
    raw_json = scrapy.Field()

    class Meta:
        indexes = (
            (("code",), True),
        )
