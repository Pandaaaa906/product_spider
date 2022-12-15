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
    mf = scrapy.Field()
    mw = scrapy.Field()
    prd_url = scrapy.Field()

    class Meta:
        indexes = (
            (("cat_no",), True),
        )


class JkProduct(scrapy.OrderedItem):
    brand = scrapy.Field()
    cat_no = scrapy.Field()
    en_name = scrapy.Field()
    cn_name = scrapy.Field()
    cas = scrapy.Field()
    purity = scrapy.Field()
    prd_url = scrapy.Field()
    img_url = scrapy.Field()

    class Meta:
        indexes = (
            (("brand", "cat_no",), True),
        )


class JKPackage(scrapy.OrderedItem):
    brand = scrapy.Field()
    cat_no = scrapy.Field()
    package = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    attrs = scrapy.Field()

    class Meta:
        indexes = (
            (('brand', 'cat_no', 'package'), True),
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
    brand = scrapy.Field()  # 品牌
    parent = scrapy.Field()  # 分类
    cat_no = scrapy.Field()  # 货号
    en_name = scrapy.Field()  # 英文名
    chs_name = scrapy.Field()  # 中文名
    cas = scrapy.Field()  # cas号
    smiles = scrapy.Field()  # 结构式
    mf = scrapy.Field()  # 分子式
    mw = scrapy.Field()  # 分子量
    stock_info = scrapy.Field()  # 库存状态  Deprecated
    purity = scrapy.Field()  # 纯度
    appearance = scrapy.Field()  # 外观
    img_url = scrapy.Field()  # 图片url
    info1 = scrapy.Field()  # 化学名称
    info2 = scrapy.Field()  # 储存条件
    info3 = scrapy.Field()
    info4 = scrapy.Field()
    info5 = scrapy.Field()

    tags = scrapy.Field()
    grade = scrapy.Field()
    mol_text = scrapy.Field()
    prd_url = scrapy.Field()  # 详情地址
    expiry_date = scrapy.Field()  # Deprecated
    stock_num = scrapy.Field()  # Deprecated
    mdl = scrapy.Field()
    einecs = scrapy.Field()
    shipping_group = scrapy.Field()  # 运输方式
    shipping_info = scrapy.Field()  # 运输条件
    attrs = scrapy.Field()  # 产品额外信息

    class Meta:
        indexes = (
            (('brand', 'cat_no',), True),
        )


class ProductPackage(scrapy.OrderedItem):
    brand = scrapy.Field()
    cat_no = scrapy.Field()
    cat_no_unit = scrapy.Field()
    package = scrapy.Field()
    cost = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    delivery_time = scrapy.Field()
    stock_num = scrapy.Field()
    info = scrapy.Field()

    attrs = scrapy.Field()  # 产品规格额外信息

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
    sub_brand = scrapy.Field()
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


class SupplierProduct(scrapy.OrderedItem):
    platform = scrapy.Field()
    source_id = scrapy.Field()
    vendor = scrapy.Field()
    brand = scrapy.Field()
    vendor_origin = scrapy.Field()
    vendor_type = scrapy.Field()
    vendor_url = scrapy.Field()

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
    synonyms = scrapy.Field()
    storage_condition = scrapy.Field()
    package = scrapy.Field()
    price = scrapy.Field()
    cost = scrapy.Field()
    delivery = scrapy.Field()

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
    currency = scrapy.Field()

    class Meta:
        indexes = (
            (('platform', 'source_id',), True),
        )


class RawSupplierQuotation(scrapy.OrderedItem):
    platform = scrapy.Field()
    source_id = scrapy.Field()
    vendor = scrapy.Field()
    brand = scrapy.Field()
    cat_no = scrapy.Field()
    package = scrapy.Field()
    discount_price = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    delivery = scrapy.Field()
    attrs = scrapy.Field()
    stock_num = scrapy.Field()
    cas = scrapy.Field()

    class Meta:
        indexes = (
            (('platform', 'source_id', 'package'), True),
        )


class ATCIndex(scrapy.OrderedItem):
    atc_code = scrapy.Field()
    drug_name = scrapy.Field()
    ddd = scrapy.Field()
    unit = scrapy.Field()
    adm = scrapy.Field()
    note = scrapy.Field()
    url = scrapy.Field()

    class Meta:
        indexes = (
            (('atc_code', 'drug_name',), True),
        )


class ChemicalItem(scrapy.OrderedItem):
    """chemical"""
    cas = scrapy.Field()
    source = scrapy.Field()  # 来源
    prd_url = scrapy.Field()
    attrs = scrapy.Field()

    class Meta:
        indexes = (
            (('source', 'cas',), True),
        )
