from string import ascii_uppercase
from urllib.parse import urljoin, urlencode

from scrapy import Request
from scrapy.http import Response

from product_spider.items import RawData
from product_spider.utils.spider_mixin import BaseSpider


def get_value(response: Response, label: str):
    ret = response.xpath(f'//li[contains(strong/text(), {label!r})]/text()').get('')
    ret = ret.replace(label, '').strip()
    return ret or None


class AllmpusSpider(BaseSpider):
    name = "allmpus"
    allowed_domains = ["allmpus.com"]
    base_url = "https://www.allmpus.com"
    start_urls = [
        f"https://www.allmpus.com/-{a}" for a in ascii_uppercase
    ]

    # API请求相关配置
    custom_settings = {
        'RETRY_TIMES': 3,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 1,
        'COOKIES_ENABLED': False,
    }

    def parse(self, response):
        nodes = response.xpath('//div[contains(@class, "product-card")]/a')
        for node in nodes:
            rel_url = node.xpath('./@href').get()
            parent = node.xpath('.//h5/text()').get('').strip() or None
            yield Request(
                urljoin(self.base_url, rel_url),
                callback=self.parse_prd_list,
                meta={'parent': parent}
            )

    def parse_prd_list(self, response):
        """解析产品列表页面（包括分类页面和搜索结果页面）"""
        # XPath: //div[a[h5]] 匹配包含产品链接的卡片
        # 从每个产品卡片中提取链接和 CAT No，然后请求详情页
        products = response.xpath('//div[a[h5]]')

        for product in products:
            rel_url = product.xpath('./a[h5]/@href').get()
            if not rel_url:
                continue
            cat_no = product.xpath('//div[a[h5]]//p[b="CAT No:"]/text()').get().strip()
            product_url = urljoin(self.base_url, rel_url)
            # 保留原有 meta（包含 task_id, keyword, search_params）
            meta = response.meta.copy()
            meta['cat_no'] = cat_no
            yield Request(
                url=product_url,
                callback=self.parse_detail,
                meta=meta,
            )


    def parse_detail(self, response):
        """解析产品详情页"""
        # 优先从页面提取 CAT No，如果页面缺失则使用 meta 中传递的 CAT No
        img_rel_url = response.xpath('//div[@class="panel-body"]//div/img/@src').get()
        img_url = img_rel_url and urljoin(self.base_url, img_rel_url)
        cat_no = get_value(response, "CAT No : ")
        parent = response.xpath('//p[strong="Category:"]/text()').get()
        d = {
            'brand': 'allmpus',
            'parent': parent or response.meta.get('parent', None),
            'cat_no': cat_no or response.meta.get('cat_no', None),
            'en_name': response.xpath('//h1/text()').get(),
            'cas': get_value(response, "CAS Number : "),
            'mf': get_value(response, "Molecular Formula : "),
            'mw': get_value(response, "Molecular Weight : "),
            'stock_info': get_value(response, "Inventory Status :"),
            'purity': get_value(response, "Purity by HPLC :"),
            'img_url': img_url,
            'info1': get_value(response, "Chemical Name :"),
            'info2': get_value(response, "Storage :"),
            'prd_url': response.url,
        }
        yield RawData(**d)

    def keyword_search(self, keyword: str, search_params: dict = None):
        """关键词搜索方法

        通过搜索接口查询产品，结果使用 parse_prd_list 解析。
        搜索结果页面结构与分类列表页面结构相同，可共用解析逻辑。
        """
        # 构建搜索URL
        search_url = f"{self.base_url}/search.php"

        # 搜索参数
        params = {'search_query': keyword}

        # 如果有额外的搜索参数，添加到URL中
        if search_params:
            params.update(search_params)

        # 返回搜索请求，添加 task_id 到 meta
        yield Request(
            url=f"{search_url}?{urlencode(params)}",
            callback=self.parse_prd_list,
            meta={
                'keyword': keyword,
                'search_params': search_params,
                'task_id': self.task_id,
            }
        )
