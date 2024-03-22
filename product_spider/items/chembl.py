import scrapyautodb as scrapy


class ChemblMolecule(scrapy.OrderedItem):
    chembl_id = scrapy.Field()
    raw_json = scrapy.Field()

    class Meta:
        indexes = (
            (("chembl_id",), True),
        )
