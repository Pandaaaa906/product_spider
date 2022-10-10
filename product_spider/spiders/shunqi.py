import json
from urllib.parse import urljoin
import scrapy
from product_spider.items import RawCompany
from product_spider.utils.spider_mixin import BaseSpider


class ShunQiWebsiteSpider(BaseSpider):
    """顺企网"""
    name = "shun_qi"
    base_url = "http://b2b.11467.com/"
    start_urls = ["http://b2b.11467.com/"]

    custom_settings = {
        "CONCURRENT_REQUESTS": "10",
        "DOWNLOAD_DELAY": 5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,

    }

    def start_requests(self):
        """当前只获取关键字为ROHS"""
        yield scrapy.Request(
            url="https://b2b.11467.com/search/7044.htm",
            callback=self.parse_list
        )

    def parse(self, response, **kwargs):
        rows = response.xpath('//div[contains(text(), "公司行业分类")]/following-sibling::div//li')
        for row in rows:
            url = urljoin(self.base_url, row.xpath("./a/@href").get())
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
            )

    def parse_list(self, response):
        urls = response.xpath("//ul[@class='companylist']/li/div[@class='f_l']//h4//a/@href").getall()
        for raw_url in urls:
            url = urljoin(self.base_url, raw_url)
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
            )
        next_url = response.xpath('//a[contains(text(), "下一页")]/@href').get()
        if next_url:
            yield scrapy.Request(
                url=urljoin(self.base_url, next_url),
                callback=self.parse_list,
            )

    def parse_detail(self, response):
        tmp_xpath = "//td[contains(text(), {!r})]/following-sibling::td//text()"
        parent = response.xpath("//div[@class='navleft']/a[last()-1]/text()").get()  # 公司分类
        raw_company_info1 = response.xpath("//dl[@class='codl']//dt[not(contains(text(), '在线QQ咨询：'))]/text()").getall()
        raw_company_info2 = response.xpath("//dl[@class='codl']//dd//text()").getall()
        company_info = json.dumps(dict(zip(raw_company_info1, raw_company_info2)), ensure_ascii=False)

        company_name = response.xpath(tmp_xpath.format("法人名称：")).get()  # 公司名称
        main_product = response.xpath(tmp_xpath.format("主要经营产品：")).get()  # 主要经营产品

        business_license_number = response.xpath(tmp_xpath.format("营业执照号码：")).get()  # 营业执照号码
        issuing_authority = response.xpath(tmp_xpath.format("发证机关：")).get()  # 发证机关
        approval_date = response.xpath(tmp_xpath.format("核准日期：")).get()  # 核准日期
        business_status = response.xpath(tmp_xpath.format("经营状态：")).get()  # 经营状态
        business_model = response.xpath(tmp_xpath.format("经营模式：")).get()  # 经营模式：

        registered_capital = response.xpath(tmp_xpath.format("注册资本：")).get()  # 注册资本

        company_url1 = response.xpath("//td[contains(text(), '公司官网：')]/following-sibling::td//a/@href").get()

        company_url2 = response.xpath("//td[contains(text(), '商铺：')]/following-sibling::td//a/@href").get()

        source_id = response.xpath(tmp_xpath.format("顺企编码：")).get()  # 顺企编码

        company_city = ''.join(response.xpath(tmp_xpath.format("所属城市：")).getall())

        company_created_time = response.xpath(tmp_xpath.format("成立时间：")).get()  # 公式成立时间

        d = {
            "parent": parent,  # 公司分类
            "company_info": company_info,  # 公司信息
            "company_name": company_name,  # 公司名称
            "main_product": main_product,  # 主要经营产品
            "business_license_number": business_license_number,  # 营业执照号码
            "issuing_authority": issuing_authority,  # 发证机关
            "approval_date": approval_date,  # 核准日期
            "business_status": business_status,  # 经营状态
            "business_model": business_model,  # 经营模式
            "registered_capital": registered_capital,  # 注册资本
            "company_url": company_url1 or company_url2,  # 公司官网
            "source_id": source_id,  # 顺企编码
            "source_url": response.url,
            "source": self.name,  # 来源
            "company_city": company_city,  # 所属城市
            "company_created_time": company_created_time  # 公司成立时间
        }

        yield RawCompany(**d)
