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


class AccPrdItem(scrapy.OrderedItem):
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
            (("cat_no",), True),
        )


class AccPrdDetail(scrapy.OrderedItem):
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
            (("cat_no",), True),
        )


class ChemServItem(scrapy.OrderedItem):
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
            (("cat_no",), True),
        )


class CDNPrdItem(scrapy.OrderedItem):
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
    mol_text = scrapy.Field()
    prd_url = scrapy.Field()

    class Meta:
        indexes = (
            (('brand', 'cat_no',), True),
        )


class ProductUnitItem(scrapy.OrderedItem):
    cat_no = scrapy.Field()
    cat_no_unit = scrapy.Field()
    unit = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()


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
