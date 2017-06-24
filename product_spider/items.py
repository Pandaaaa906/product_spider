# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
import scrapy


class JkItem(scrapy.Item):
    cat_no = scrapy.Field()
    en_name = scrapy.Field()
    chs_name = scrapy.Field()
    cas = scrapy.Field()
    brand = scrapy.Field()
    package = scrapy.Field()
    price = scrapy.Field()
    purity = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class AccPrdItem(scrapy.Item):
    cat_no = scrapy.Field()
    catalog = scrapy.Field()
    name = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    description = scrapy.Field()
    stock_info = scrapy.Field()
    prd_url = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class AccPrdDetail(scrapy.Item):
    cat_no = scrapy.Field()
    n_components = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    storage = scrapy.Field()
    l_components = scrapy.Field()
    cas = scrapy.Field()
    mp = scrapy.Field()
    bp = scrapy.Field()
    fp = scrapy.Field()
    ghs = scrapy.Field()
    un_num = scrapy.Field()
    pk_group = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class ChemServItem(scrapy.Item):
    cat_no = scrapy.Field()
    name = scrapy.Field()
    synonyms = scrapy.Field()
    unit = scrapy.Field()
    cas = scrapy.Field()
    price = scrapy.Field()
    stock_available = scrapy.Field()
    catalog = scrapy.Field()
    shipment = scrapy.Field()
    concn = scrapy.Field()
    solvent = scrapy.Field()
    current_lot = scrapy.Field()
    url = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class CDNPrdItem(scrapy.Item):
    cat_no = scrapy.Field()
    name = scrapy.Field()
    unit = scrapy.Field()
    cas = scrapy.Field()
    purity = scrapy.Field()
    price = scrapy.Field()
    stock = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no', 'unit'), True),
        )


class BestownPrdItem(scrapy.Item):
    chs_name = scrapy.Field()
    en_name = scrapy.Field()
    country = scrapy.Field()
    brand = scrapy.Field()
    unit = scrapy.Field()
    cat_no_unit = scrapy.Field()
    prd_type = scrapy.Field()
    stock = scrapy.Field()
    coupon = scrapy.Field()
    price = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no_unit',),True),
        )


class TLCPrdItem(scrapy.Item):
    name = scrapy.Field()
    cat_no = scrapy.Field()
    img_url = scrapy.Field()
    cas = scrapy.Field()
    wm = scrapy.Field()
    mf = scrapy.Field()
    info = scrapy.Field()
    api_name = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class NicpbpItem(scrapy.Item):
    cat_no = scrapy.Field()
    name = scrapy.Field()
    lot = scrapy.Field()
    unit = scrapy.Field()
    usage = scrapy.Field()
    storage = scrapy.Field()
    in_stock = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",),True),
        )


class DaltonItem(scrapy.Item):
    name = scrapy.Field()
    url_prd = scrapy.Field()
    mol_text = scrapy.Field()
    purity = scrapy.Field()
    cat_no = scrapy.Field()
    cas = scrapy.Field()
    stock = scrapy.Field()
    mol = scrapy.Field()
    catalog = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no',), True),
        )