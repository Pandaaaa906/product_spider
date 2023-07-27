import scrapyautodb as scrapy

"""
国家兽药基础数据库
"""


class CVDRegData(scrapy.OrderedItem):
    byx = scrapy.Field()
    bz = scrapy.Field()  # 备注
    gg = scrapy.Field()  # 规格
    ggh = scrapy.Field()  # 公告号
    ggrq = scrapy.Field()  # 公告日期
    itemid = scrapy.Field()
    lb = scrapy.Field()  # 类别
    shren = scrapy.Field()
    shrq = scrapy.Field()  # 上市日期
    syz = scrapy.Field()  # 适应症
    xsymc = scrapy.Field()  # 新兽药名称
    yzdw = scrapy.Field()  # 研制单位
    zsh = scrapy.Field()  # 证书号

    class Meta:
        indexes = (
            (("itemid",), True),
        )


class CVDClinicalData(scrapy.OrderedItem):
    byx = scrapy.Field()
    itemid = scrapy.Field()
    nlcsydd = scrapy.Field()
    pjh = scrapy.Field()
    shren = scrapy.Field()
    shrq = scrapy.Field()
    slh = scrapy.Field()
    sqdwlxr = scrapy.Field()
    sqdwmc = scrapy.Field()
    szcpph = scrapy.Field()
    szcpsl = scrapy.Field()
    xmmc = scrapy.Field()
    yxqjz = scrapy.Field()
    yxqks = scrapy.Field()
    yxqx = scrapy.Field()
    zsdwmc = scrapy.Field()

    class Meta:
        indexes = (
            (("itemid",), True),
        )


class CVDBioInspectData(scrapy.OrderedItem):
    bcscqy = scrapy.Field()
    bcydwmc = scrapy.Field()
    bhgxm = scrapy.Field()
    byx = scrapy.Field()
    bz = scrapy.Field()
    cjhj = scrapy.Field()
    cpmc = scrapy.Field()
    cpwh = scrapy.Field()
    itemid = scrapy.Field()
    jd = scrapy.Field()
    jydw = scrapy.Field()
    jyjl = scrapy.Field()
    jylb = scrapy.Field()
    jyxm = scrapy.Field()
    jyyj = scrapy.Field()
    nd = scrapy.Field()
    ph = scrapy.Field()
    pzwhitemid = scrapy.Field()
    shren = scrapy.Field()
    shrq = scrapy.Field()

    class Meta:
        indexes = (
            (("itemid",), True),
        )
