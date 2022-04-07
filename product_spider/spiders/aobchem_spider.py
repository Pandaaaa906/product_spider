from scrapy import Request
from product_spider.items import RawData, ProductPackage
from product_spider.utils.spider_mixin import BaseSpider


class AobchemSpider(BaseSpider):
    name = "aobchem"
    allowed_domains = ["aobchem.com.cn"]
    start_urls = ["http://www.aobchem.com.cn/product/466.html"]

    def parse(self, response, **kwargs):
        urls = response.xpath("//div[@class='col-lg-2 col-md-3 col-sm-4 col-xs-12 kj_pronyimg']//a/@href").getall()
        for url in urls:
            url = "http:" + url
            if url:
                yield Request(
                    url,
                    callback=self.parse_detail,
                )

        next_url = "http:" + response.xpath("//nav[@class='text-center kj_product_page']//span[last()-2]/a/@href").get()
        if next_url:
            yield Request(
                next_url,
                callback=self.parse
            )

    def parse_detail(self, response):
        cat_no = response.xpath("//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), '产品编号')]/following-sibling::td/text()").get()
        parent = response.xpath("//ol[@class='breadcrumb']/li[last()]/a/text()").get()
        en_name = response.xpath("//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), '英文名')]/following-sibling::td/text()").get()
        chs_name = response.xpath("//div[@class=' col-lg-8 col-md-8 col-sm-7 col-xs-12 kj_promcxx']/h1/span/text()").get()
        cas = response.xpath("//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), 'CAS号')]/following-sibling::td/text()").get()
        mw = response.xpath("//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), '分子量')]/following-sibling::td/text()").get()
        mf = ''.join(response.xpath('//td[text()="分子式"]/following-sibling::td[1]//text()').getall())
        prd_url = response.url
        img_url = response.xpath("//div[@class='item active']/img/@src").get()
        img_url = "http:" + img_url
        mdl = response.xpath("//div[@class='table-responsive kj_cplb']//tr//td[contains(text(), 'MDL')]/following-sibling::td/text()").get()
        info1 = response.xpath("//td[@class='kj_sjbm']//text()").get()

        d = {
            "brand": self.name,
            "parent": parent,
            "cat_no": cat_no,
            "en_name": en_name,
            "chs_name": chs_name,
            "cas": cas,
            "mw": mw,
            "mf": mf,
            "prd_url": prd_url,
            "img_url": img_url,
            "mdl": mdl,
            "info1": info1
        }
        yield RawData(**d)

        rows = response.xpath("//table[@class='table kj_taxsto']//tr[position()>1]")
        for row in rows:
            price = row.xpath(".//td[@class='text-center'][last()-1]//span/text()").get()
            package = row.xpath(".//td[@class='text-center']/text()").get()
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": price,
                "currency": "USD"
            }
            yield ProductPackage(**dd)

