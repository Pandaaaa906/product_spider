import scrapyautodb as scrapy


class ChemSrcChemical(scrapy.OrderedItem):
    chemsrc_id = scrapy.Field()
    chemsrc_update_time = scrapy.Field()
    url = scrapy.Field()

    generic_name = scrapy.Field()  # 常用名
    en_name = scrapy.Field()  # 英文名
    cas = scrapy.Field()  # CAS
    mw = scrapy.Field()  # 分子量
    mf = scrapy.Field()  # 分子式
    density = scrapy.Field()  # 密度
    boiling_point = scrapy.Field()  # 沸点
    melting_point = scrapy.Field()  # 熔点
    flash_point = scrapy.Field()  # 闪点

    data_category = scrapy.Field()  # 产品性质目录
    content_html = scrapy.Field()  #

    class Meta:
        indexes = (
            (('chemsrc_id',), True),
        )
