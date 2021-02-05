# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html
# import scrapy
import scrapyautodb as scrapy


class JkItem(scrapy.OrderedItem):
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
            (("cat_no",), True),
        )


class BestownPrdItem(scrapy.OrderedItem):
    chs_name = scrapy.Field()
    en_name = scrapy.Field()
    country = scrapy.Field()
    brand = scrapy.Field()
    unit = scrapy.Field()
    cas = scrapy.Field()
    cat_no_unit = scrapy.Field()
    prd_type = scrapy.Field()
    stock = scrapy.Field()
    coupon = scrapy.Field()
    price = scrapy.Field()
    url = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no_unit',), True),
        )


class NicpbpItem(scrapy.OrderedItem):
    cat_no = scrapy.Field()
    name = scrapy.Field()
    lot = scrapy.Field()
    unit = scrapy.Field()
    usage = scrapy.Field()
    storage = scrapy.Field()
    in_stock = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",), True),
        )


class RawData(scrapy.OrderedItem):
    brand = scrapy.Field()
    parent = scrapy.Field()
    cat_no = scrapy.Field()
    en_name = scrapy.Field()
    chs_name = scrapy.Field()
    cas = scrapy.Field()
    smiles = scrapy.Field()
    mf = scrapy.Field()
    mw = scrapy.Field()
    stock_info = scrapy.Field()
    purity = scrapy.Field()
    appearance = scrapy.Field()
    img_url = scrapy.Field()
    info1 = scrapy.Field()
    info2 = scrapy.Field()
    info3 = scrapy.Field()
    info4 = scrapy.Field()
    info5 = scrapy.Field()

    tags = scrapy.Field()
    grade = scrapy.Field()
    mol_text = scrapy.Field()
    prd_url = scrapy.Field()
    expiry_date = scrapy.Field()
    stock_num = scrapy.Field()
    mdl = scrapy.Field()
    einecs = scrapy.Field()

    class Meta:
        indexes = (
            (('brand', 'cat_no',), True),
        )


class ProductPackage(scrapy.OrderedItem):
    brand = scrapy.Field()
    cat_no = scrapy.Field()
    cat_no_unit = scrapy.Field()
    package = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    delivery_time = scrapy.Field()
    stock_num = scrapy.Field()
    info = scrapy.Field()

    class Meta:
        indexes = (
            (('brand', 'cat_no', 'package'), True),
        )


class TanmoItem(scrapy.OrderedItem):
    cat_no = scrapy.Field()
    name = scrapy.Field()
    standard = scrapy.Field()
    cas = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    stock = scrapy.Field()
    delivery = scrapy.Field()
    expiry_date = scrapy.Field()
    company = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no', 'name'), True),
        )


class AnpelItem(scrapy.OrderedItem):
    cat_no = scrapy.Field()
    cn_name = scrapy.Field()
    en_name = scrapy.Field()
    brand = scrapy.Field()
    cas = scrapy.Field()
    package = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    delivery_time = scrapy.Field()
    storage = scrapy.Field()
    prd_url = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no',), True),
        )


class NewBestownItem(scrapy.OrderedItem):
    uid = scrapy.Field()
    stockcode = scrapy.Field()
    name = scrapy.Field()
    brand = scrapy.Field()
    purity = scrapy.Field()
    name2 = scrapy.Field()
    name3 = scrapy.Field()
    pack = scrapy.Field()
    molecular = scrapy.Field()
    picture = scrapy.Field()
    picture2 = scrapy.Field()
    date = scrapy.Field()
    temp = scrapy.Field()
    method = scrapy.Field()
    transport = scrapy.Field()
    attention = scrapy.Field()
    price = scrapy.Field()
    num = scrapy.Field()
    msds = scrapy.Field()
    report = scrapy.Field()
    rj = scrapy.Field()

    class Meta:
        indexes = (
            (('stockcode',), True),
        )


class HbErmItem(scrapy.OrderedItem):
    cat_no = scrapy.Field()
    cn_name = scrapy.Field()
    batch = scrapy.Field()
    manufacture = scrapy.Field()
    expire_date = scrapy.Field()
    package = scrapy.Field()
    sale_info = scrapy.Field()
    usage = scrapy.Field()
    components = scrapy.Field()
    concentrate = scrapy.Field()

    price = scrapy.Field()
    stock_info = scrapy.Field()

    class Meta:
        indexes = (
            (('cat_no', 'batch'), True),
        )


class HongmengItem(scrapy.OrderedItem):
    brand = scrapy.Field()
    sub_brand = scrapy.Field()
    parent = scrapy.Field()
    cat_no = scrapy.Field()
    sub_cat_no = scrapy.Field()
    cn_name = scrapy.Field()
    purity = scrapy.Field()
    cas = scrapy.Field()
    package = scrapy.Field()
    price = scrapy.Field()
    amount = scrapy.Field()
    place_code = scrapy.Field()
    prd_url = scrapy.Field()

    class Meta:
        indexes = (
            (('brand', 'sub_brand', 'cat_no', 'sub_cat_no', 'place_code'), True),
        )
