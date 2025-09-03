from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import get_url
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.spider_mixin import BaseSpider


class PurechemlandSpider(BaseSpider):
    name = "purechemland"
    start_urls = ["https://purechemland.shop/", ]
    base_url = "https://purechemland.com/"
    brand = 'purechemland'
    custom_settings = {
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        # 'DOWNLOADER_MIDDLEWARES': {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'RETRY_ENABLED': True,
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'RETRY_BACKOFF_BASE': 2,
        'RETRY_BACKOFF_MAX': 60,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        )
    }
    currency = 'RMB'

    def parse(self, response, **kwargs):
        rel_urls = response.xpath("//ul[@id='subNav']//a[contains(@href,'/product_categories/')]/@href").getall()
        for rel_url in set(rel_urls):
            url = get_url(response.url, rel_url)
            yield Request(url, self.parse_list)

    def parse_list(self, response):
        product_urls = response.xpath("//tbody[@id='goodList']/tr/td/a/@href").getall()
        parent = response.xpath("//span[@id='titlename']/text()").get()
        for product_url in set(product_urls):
            product_url = get_url(response.url, product_url)
            yield Request(product_url, self.parse_detail, meta={'parent': parent})

        next_url = response.xpath("//a[@rel='next']/@href").get()
        if next_url:
            next_url = get_url(response.url, next_url)
            yield Request(next_url, self.parse_list)

    def parse_detail(self, response):
        brand = response.xpath("//dt[contains(text(),'品牌')]/following-sibling::*[1]//text()").get()
        if brand and 'PCL' not in brand.upper():
            return
        cat_no = response.xpath("//dt[contains(text(),'产品编号')]/following-sibling::*[1]//text()").get()
        if not cat_no:
            good_info_list = response.xpath("//div[@class='goods-info-list']")
            if not good_info_list:
                return
            else:
                self.logger.info('Call parse_detail2')
                yield from self.parse_detail2(response)
                return
        cas = response.xpath("//dt[contains(text(),'CAS')]/following-sibling::*[1]//text()").get()
        if cas and 'N/A' in cas:
            cas = None
        img_url = response.xpath("//img[@id='current-img']/@src").get()
        if img_url:
            if '/store/img/default.png' in img_url:
                img_url = None
            else:
                img_url = get_url(response.url, img_url)

        cat_no = cat_no.replace('PCL-#-', '')
        d = {
            "brand": self.brand,
            "parent": response.meta.get("parent"),
            "cat_no": cat_no,
            "chs_name": response.xpath("//h1[@class='tit']/text()").get(),
            "en_name": response.xpath("//p[@class='subtitle']/text()").get(),
            "cas": cas,
            "prd_url": response.url,
            "img_url": img_url,
            'purity': response.xpath("//dt[contains(text(),'产品特性描述')]/following-sibling::*[1]//text()").get()
        }

        yield RawData(**d)
        price = response.xpath("//*[@id='price']//text()").get()
        if price:
            price = price.replace("¥", '')
        package = response.xpath("//dt[contains(text(),'包装')]/following-sibling::*[1]//text()").get()
        dd = {
            "brand": self.name,
            "cat_no": d['cat_no'],
            "package": package,
            "cost": price,
            "price": price,
            "currency": self.currency,
            'purity': d['purity'],
            'stock_num': response.xpath("//dt[contains(text(),'库存')]/following-sibling::*[1]//text()").get(),
        }
        yield ProductPackage(**dd)

    # 适配第二种布局 https://purechemland.shop/products/40557
    def parse_detail2(self, response):
        product_trs = response.xpath("//div[@class='goods-info-list']/table/tbody/tr")
        headers = response.xpath("//div[@class='goods-info-list']/table/thead//th/text()").getall()
        headers = [x.strip() for x in headers]
        property_map = {}
        for index, th in enumerate(headers):
            property_map[th] = index

        chs_name = response.xpath("//h1[@class='tit']/text()").get()
        en_name = response.xpath("//p[@class='subtitle']/text()").get()
        cas = response.xpath("//dt[contains(text(),'CAS')]/following-sibling::*[1]//text()").get()
        img_url = response.xpath("//img[@id='current-img']/@src").get()
        if img_url:
            if '/store/img/default.png' in img_url:
                img_url = None
            else:
                img_url = get_url(response.url, img_url)
        if cas and 'N/A' in cas:
            cas = None
        for tr in product_trs:
            tds = tr.xpath('./td')
            d = {
                "brand": self.brand,
                "parent": response.meta.get("parent"),
                "cat_no": tds[property_map.get('货号')].xpath('.//text()').get(),
                "chs_name": chs_name,
                "en_name": en_name,
                "cas": cas,
                "prd_url": response.url,
                "img_url": img_url,
                'purity': tds[property_map.get('规格型号')].xpath('.//text()').get(),
            }
            yield RawData(**d)
            price = tds[property_map.get('目录价')].xpath('./span/text()').get()
            if price:
                price = price.replace("¥", '')
            dd = {
                "brand": self.brand,
                "cat_no": d['cat_no'],
                "package": tds[property_map.get('参数说明')].xpath('.//text()').get(),
                'price': price,
                'cost': price,
                "currency": 'RMB',
                'purity': tds[property_map.get('规格型号')].xpath('.//text()').get(),
                'delivery_time': tds[property_map.get('货期')].xpath('.//text()').get(),
            }
            yield ProductPackage(**dd)
