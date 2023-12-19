import scrapyautodb as scrapy


class ChinaDrugTrial(scrapy.OrderedItem):
    code = scrapy.Field()
    status = scrapy.Field()
    applier = scrapy.Field()
    first_publish_date = scrapy.Field()

    drug_name = scrapy.Field()
    drug_type = scrapy.Field()

    test_title = scrapy.Field()
    test_common_title = scrapy.Field()
    version = scrapy.Field()
    version_date = scrapy.Field()

    contact = scrapy.Field()
    contact_phone = scrapy.Field()
    contact_mobile = scrapy.Field()
    contact_email = scrapy.Field()
    contact_addr = scrapy.Field()
    contact_post_code = scrapy.Field()

    research_org = scrapy.Field()
    research_contact = scrapy.Field()
    research_degree = scrapy.Field()
    research_title = scrapy.Field()
    research_phone = scrapy.Field()
    research_email = scrapy.Field()
    research_addr = scrapy.Field()
    research_post_code = scrapy.Field()

    html = scrapy.Field()
