import json
import scrapy
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


def is_heowns(brand: str):
    return brand == '希恩思'


class HeownsSpider(BaseSpider):
    """希恩思"""
    """其他品牌: {'TCI', 'Solarbio', '南京飞虎', '福来兹', '进口分装', 'CIL'}"""
    name = "heowns"
    start_urls = ["http://www.heowns.com/products/258.html"]
    other_brands = set()

    def parse(self, response, **kwargs):
        rows = response.xpath("//div[@class='kj-product-item']//div[@class='kj-proitembox']")
        for row in rows:
            url = row.xpath(".//div[@class='col-lg-3  col-md-3  col-xs-4  col-sm-4 kj-product-list']/a/@href").get()
            pd_id = row.xpath(".//input[@name='productitem']/@value").get()
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={
                    "pd_id": pd_id,
                }
            )
        # 翻页
        next_page = response.xpath(
            '//ul[contains(@class, "pagination")]/li[@class="active"]/following-sibling::li[1]/a/text()'
        ).get()
        if next_page:
            yield scrapy.Request(
                url=f"http://www.heowns.com/products/258.html?page={next_page}&prop_filter=%7b%7d",
                callback=self.parse
            )

    def parse_detail(self, response):
        pd_id = response.meta.get("pd_id")
        chs_name = response.xpath("//th[contains(text(), '中文名称:')]/following-sibling::td/text()").get()
        en_name = response.xpath("//th[contains(text(), '英文名称:')]/following-sibling::td/text()").get()
        cas = response.xpath("//th[contains(text(), 'CAS.No:')]/following-sibling::td/text()").get()
        mf = ''.join(response.xpath("//th[contains(text(), '分子式:')]/following-sibling::td//text()").getall())
        mw = response.xpath("//th[contains(text(), '分子量:')]/following-sibling::td/text()").get()
        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        if parent == '产品分类':
            parent = None
        img_url = response.xpath("//div[@class='item active']/img/@src").get()
        d = {
            "chs_name": chs_name,
            "en_name": en_name,
            "cas": cas,
            "mf": mf,
            "mw": mw,
            "parent": parent,
            "img_url": img_url,
            "prd_url": response.url,
        }

        yield scrapy.FormRequest(
            url="http://www.heowns.com/index.aspx",
            callback=self.parse_package,
            method='POST',
            formdata={
                "a": "loadgoodbyajax",
                "pd_id": pd_id,
            },
            meta={
                "product": d,
                "pd_id": pd_id,
            }
        )

    def parse_package(self, response):
        d = response.meta.get("product")
        pd_id = response.meta.get("pd_id")
        j_obj = json.loads(response.text)
        results = json.loads(j_obj["value"].get("ObjResult")).get(f"p_{pd_id}")
        for result in results:
            package_info = json.loads(result.get("Goods_info")).get("goodsinfo")
            package = package_info.get("packaging")
            purity = package_info.get("purity")
            brand = package_info.get("brand")
            if brand == '促销无折扣':
                brand = "希恩思"
            for i in result.get("Inventores"):
                cat_no = i.get("Goods_no")
                price = i.get("Price")
                d["brand"] = brand
                d["cat_no"] = cat_no
                d["purity"] = purity
                dd = {
                    "cat_no": cat_no,
                    "price": price,
                    "currency": "RMB",
                    "package": package,
                    "brand": brand
                }
                if not is_heowns(brand):
                    self.other_brands.add(brand)
                    # TODO yield SupplierProduct
                    return
                yield RawData(**d)
                yield ProductPackage(**dd)

    def closed(self, reason):
        self.logger.info(f'其他品牌: {self.other_brands}')
