import scrapyautodb as scrapy


class EChemPortalItem(scrapy.OrderedItem):
    echem_id = scrapy.Field()
    name = scrapy.Field()
    number = scrapy.Field()
    name_type = scrapy.Field()
    number_type = scrapy.Field()
    level = scrapy.Field()
    cnl_flag = scrapy.Field()
    endpoint_data = scrapy.Field()
    classified = scrapy.Field()
    labelling_list = scrapy.Field()
    classification_list = scrapy.Field()
    qualifier = scrapy.Field()
    cnl_url = scrapy.Field()
    participant_id = scrapy.Field()
    participant_acronym = scrapy.Field()
    participant_types_localized = scrapy.Field()
    participant_provides_property_data = scrapy.Field()
    url = scrapy.Field()
    remark = scrapy.Field()
    attrs = scrapy.Field()  # extra data fields, json

    class Meta:
        indexes = (
            (("echem_id",), True),
        )
