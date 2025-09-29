import json
from urllib.parse import urljoin

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip, get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider


class AltaSpider(BaseSpider):
    """阿尔塔"""
    name = "alta"
    brand = 'alta'
    base_url = "http://www.altascientific.com/"
    start_urls = ['http://www.altascientific.com/', ]
    additional_keywords = ['混标', 'solution']

    def parse(self, response, **kwargs):
        for keyword in self.additional_keywords:
            url = f'https://www.altascientific.cn/product/search.php?key_1={keyword}&Submit2.x=14&Submit2.y=17'
            yield Request(url, callback=self.parse_search_list)
        a_nodes = response.xpath('//li[position()<7]//li[not(ul)]/a')
        for a in a_nodes:
            parent = a.xpath('./text()').get()
            rel_url = a.xpath('./@href').get()
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_list, meta={'parent': parent})

    def parse_search_list(self, response):
        trs = response.xpath('//div[@id="newsquery"]//tr')
        if not trs:
            self.logger.info(f"No result in url:{response.url}")
            return
        theads = trs[0].xpath('./td')
        parent_index = None
        for index, thead in enumerate(theads):
            _text = thead.xpath('./div/text()').get()
            if _text and '分类' in _text:
                parent_index = index
        for tr in trs[1:]:
            rel_url = tr.xpath('.//a[@class="linkall"]/@href').get()
            if not rel_url:
                continue

            parent: str = None
            if parent_index:
                if parent := tr.xpath(f'./td[{parent_index + 1}]/div/text()').get():
                    parent = parent.strip()
                    if parent.startswith('NA'):
                        parent = None
                    else:
                        # parent: 杀虫剂 Insecticides
                        parent = parent.split(' ')[0]
            yield Request(
                get_url(response.url, rel_url),
                callback=self.parse_detail,
                meta={'parent': parent},
            )

    def parse_list(self, response):
        parent = response.meta.get('parent')
        children_urls = response.xpath("//div[@class='featured-products']//a/@href").getall()
        rel_urls = response.xpath('//a[@class="linkall"]/@href').getall()
        if children_urls:
            for url in children_urls:
                yield Request(
                    url=urljoin("https://www.altascientific.cn/product/", url),
                    callback=self.parse_list,
                    meta={'parent': parent},
                )
        else:
            for rel_url in rel_urls:
                yield Request(
                    urljoin(response.url, rel_url),
                    callback=self.parse_detail,
                    meta={'parent': parent}
                )
            next_url = response.xpath('//a[contains(text(), "下一页")]/@href').get()
            if next_url:
                yield Request(
                    url=urljoin("https://www.altascientific.cn/product/", next_url),
                    callback=self.parse_list,
                    meta={'parent': parent},
                )

    def parse_detail(self, response):
        tmp = 'normalize-space(//td[contains(div/text(), {!r})]/following-sibling::td/text())'
        rel_img = response.xpath('//div[@class="c_c_p"]//div/img/@src').get()
        cat_no = strip(response.xpath(tmp.format("产品号/Catalog#")).get())
        synonyms = strip(response.xpath(tmp.format("Synonyms：")).get())

        # 其他产品信息
        product_info = response.xpath("//table[@class='c_c_p_1']//tr[last()]//td[last()]//p[last()-1]/text()").get()
        # 其他产品信息图片
        product_info_img = response.xpath("//table[@class='c_c_p_1']//tr[last()]//td[last()]//p[last()]//@src").get()

        prd_attrs = json.dumps({
            "synonyms": synonyms,
            "product_info": product_info,
            "product_info_img": product_info_img,
        })

        d = {
            'brand': self.brand,
            'parent': response.meta.get('parent'),
            'cat_no': cat_no,
            'en_name': strip(response.xpath(tmp.format("Product Name：")).get()),
            'chs_name': strip(response.xpath(tmp.format("产品名称：")).get()),
            'cas': strip(response.xpath(tmp.format("CAS#：")).get()),
            'mf': strip(response.xpath(tmp.format("分子式/Formula：")).get()),
            'mw': strip(response.xpath(tmp.format("分子量/MW：")).get()),
            'purity': strip(response.xpath(tmp.format("纯度/Purity (%)：")).get()),
            'info1': strip(response.xpath(tmp.format("Synonyms：")).get()),
            'info2': strip(response.xpath(tmp.format("储藏条件/Storage：")).get()),
            'appearance': strip(response.xpath(tmp.format("颜色/Color：")).get()),
            'shipping_info': strip(response.xpath(tmp.format("运输条件/Transportation：")).get()),
            'mdl': strip(response.xpath(tmp.format("MDL#：")).get()),
            "attrs": prd_attrs,
            'img_url': rel_img and urljoin(response.url, rel_img),
            'prd_url': response.url,
        }
        for k in d:
            d[k] = d[k] if d[k] != 'NA' else None
        yield RawData(**d)
        ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
        yield SupplierProduct(**ddd)

        rows = response.xpath('//table[@class="c_p_size"]//tr[td and td/text()!="NA"]')
        for row in rows:
            if (cost := row.xpath('./td[2]/text()').get()) == 'NA':
                cost = None
            package = parse_package(row.xpath('./td[1]/text()').get())
            delivery_time = row.xpath('./td[3]/text()').get()
            # sub_brand = row.xpath("./td[4]/text()").get()  # Not sure why

            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': cost,
                "delivery_time": delivery_time,
                'currency': 'RMB',
                'purity': d.get('purity'),
            }
            yield ProductPackage(**dd)

            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)
            yield RawSupplierQuotation(**dddd)
