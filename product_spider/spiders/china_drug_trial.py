from scrapy import FormRequest, Request
from scrapy.http import Response

from product_spider.items import ChinaDrugTrial
from product_spider.utils.spider_mixin import BaseSpider


class ChinaDrugTrialSpider(BaseSpider):
    name = 'china_drug_trial'
    url_detail = 'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml'
    url_search = 'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml'
    start_urls = [url_search]

    custom_settings = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        }
    }

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={"playwright": True})

    def parse(self, response, **kwargs):
        ids = response.xpath('//td[2]/a/@id').getall()
        for _id in ids:
            yield FormRequest(self.url_detail, formdata={
                "id": _id,
            }, callback=self.parse_detail)
        # next page
        pass

    def parse_detail(self, response: Response):
        tmpl = '//th[contains(text(), {!r})]/following-sibling::td[1]/text()'
        d = {
            "code": response.xpath(tmpl.format("登记号")).get(),
            "status": response.xpath(tmpl.format("试验状态")).get(),
            "applier": response.xpath(tmpl.format("申请人名称")).get(),
            "first_publish_date": response.xpath(tmpl.format("首次公示信息日期")).get(),
            "drug_name":  response.xpath(tmpl.format("药物名称")).get(),
            "drug_type":  response.xpath(tmpl.format("药物类型")).get(),
            "test_title":  response.xpath(tmpl.format("试验专业题目")).get(),
            "test_common_title":  response.xpath(tmpl.format("试验通俗题目")).get(),
            "version":  response.xpath(tmpl.format("方案最新版本号	")).get(),
            "version_date":  response.xpath(tmpl.format("版本日期:")).get(),
            "contact":  response.xpath(tmpl.format("联系人姓名")).get(),
            "contact_phone":  response.xpath(tmpl.format("联系人座机")).get(),
            "contact_mobile":  response.xpath(tmpl.format("联系人手机号")).get(),
            "contact_email":  response.xpath(tmpl.format("联系人Email")).get(),
            "contact_addr":  response.xpath(tmpl.format("联系人邮政地址")).get(),
            "contact_post_code":  response.xpath(tmpl.format("联系人邮编")).get(),

            "research_org":  response.xpath(tmpl.format("单位名称")).get(),
            "research_contact":  response.xpath(tmpl.format("姓名")).get(),
            "research_degree":  response.xpath(tmpl.format("学位")).get(),
            "research_title":  response.xpath(tmpl.format("职称")).get(),
            "research_phone": response.xpath(tmpl.format("电话")).get(),
            "research_email": response.xpath(tmpl.format("Email")).get(),
            "research_addr": response.xpath(tmpl.format("邮政地址")).get(),
            "research_post_code": response.xpath(tmpl.format("邮编")).get(),

            "html": response.text,
        }
        yield ChinaDrugTrial(**d)
