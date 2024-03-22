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


class ChemicalBookChemical(scrapy.OrderedItem):
    cb_id = scrapy.Field()
    cn_name = scrapy.Field()
    en_name = scrapy.Field()
    cn_synonyms = scrapy.Field()
    en_synonyms = scrapy.Field()

    cas = scrapy.Field()
    mf = scrapy.Field()
    mw = scrapy.Field()
    einecs = scrapy.Field()
    categories = scrapy.Field()
    mol_url = scrapy.Field()
    img_url = scrapy.Field()

    url = scrapy.Field()
    attrs = scrapy.Field()
    html = scrapy.Field()

    class Meta:
        indexes = (
            (("cb_id",), True),
        )
