import re
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request, FormRequest

from product_spider.items import AnpelItem
from product_spider.utils.spider_mixin import BaseSpider


def gen_post_data(target, to_page, view_state, view_state_generator, event_validation):
    parsed_target = target.replace("_", "$")
    return {
        'ScriptManager': f'UpdatePanel1|{parsed_target}',
        'txtSear': '',
        'gridview$ctl02$lblNewPrice1': '0',
        'gridview$ctl02$txtTrnQty': '1',
        'gridview$ctl03$lblNewPrice1': '0',
        'gridview$ctl03$txtTrnQty': '1',
        'gridview$ctl04$lblNewPrice1': '0',
        'gridview$ctl04$txtTrnQty': '1',
        'gridview$ctl05$lblNewPrice1': '0',
        'gridview$ctl05$txtTrnQty': '1',
        'gridview$ctl06$lblNewPrice1': '0',
        'gridview$ctl06$txtTrnQty': '1',
        'gridview$ctl07$lblNewPrice1': '0',
        'gridview$ctl07$txtTrnQty': '1',
        'gridview$ctl08$lblNewPrice1': '0',
        'gridview$ctl08$txtTrnQty': '1',
        'gridview$ctl09$lblNewPrice1': '0',
        'gridview$ctl09$txtTrnQty': '1',
        'gridview$ctl10$lblNewPrice1': '0',
        'gridview$ctl10$txtTrnQty': '1',
        'gridview$ctl11$lblNewPrice1': '0',
        'gridview$ctl11$txtTrnQty': '1',
        'gridview$ctl12$lblNewPrice1': '0',
        'gridview$ctl12$txtTrnQty': '1',
        'gridview$ctl13$lblNewPrice1': '0',
        'gridview$ctl13$txtTrnQty': '1',
        'gridview$ctl14$lblNewPrice1': '0',
        'gridview$ctl14$txtTrnQty': '1',
        'gridview$ctl15$lblNewPrice1': '0',
        'gridview$ctl15$txtTrnQty': '1',
        'gridview$ctl16$lblNewPrice1': '0',
        'gridview$ctl16$txtTrnQty': '1',
        'gridview$ctl17$lblNewPrice1': '0',
        'gridview$ctl17$txtTrnQty': '1',
        'gridview$ctl18$lblNewPrice1': '0',
        'gridview$ctl18$txtTrnQty': '1',
        'gridview$ctl19$lblNewPrice1': '0',
        'gridview$ctl19$txtTrnQty': '1',
        'gridview$ctl20$lblNewPrice1': '0',
        'gridview$ctl20$txtTrnQty': '1',
        'gridview$ctl21$lblNewPrice1': '0',
        'gridview$ctl21$txtTrnQty': '1',
        'gridview$ctl22$lblNewPrice1': '0',
        'gridview$ctl22$txtTrnQty': '1',
        'gridview$ctl23$lblNewPrice1': '0',
        'gridview$ctl23$txtTrnQty': '1',
        'gridview$ctl24$lblNewPrice1': '0',
        'gridview$ctl24$txtTrnQty': '1',
        'gridview$ctl25$lblNewPrice1': '0',
        'gridview$ctl25$txtTrnQty': '1',
        'gridview$ctl26$lblNewPrice1': '0',
        'gridview$ctl26$txtTrnQty': '1',
        'gridview$ctl27$lblNewPrice1': '0',
        'gridview$ctl27$txtTrnQty': '1',
        'gridview$ctl28$lblNewPrice1': '0',
        'gridview$ctl28$txtTrnQty': '1',
        'gridview$ctl29$lblNewPrice1': '0',
        'gridview$ctl29$txtTrnQty': '1',
        'txtToPageNum': to_page,
        '__EVENTTARGET': parsed_target,
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
        '__ASYNCPOST': 'true',
    }


class AnpelSpider(BaseSpider):
    name = "anpel_prds"
    base_url = 'https://www.anpel.com.cn/'
    start_urls = [
        'https://www.anpel.com.cn/Brands_0032.html',  # anpel
        # 'https://www.anpel.com.cn/Brands_0134.html',  # cnw
        # 'https://www.anpel.com.cn/Brands_0181.html',  # o2si
    ]

    def parse(self, response):
        rel_urls = response.xpath('//a[@class="Stkno"]/@href').extract()
        for rel_url in rel_urls:
            yield Request(urljoin(self.base_url, rel_url), callback=self.detail_parse)

        next_page = response.xpath('//a[contains(@style,"background-color:#0088FF;")]/../following-sibling::td/a')
        if not next_page:
            return
        target = next_page.xpath('./@id').get()
        to_page = next_page.xpath('./text()').get()

        view_state = response.xpath('//input[@id="__VIEWSTATE"]/@value').get('')
        view_state = view_state or first(re.findall(r'__VIEWSTATE\|([^|]+)', response.text))

        view_state_generator = response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get('')
        view_state_generator = view_state_generator or first(re.findall(r'__VIEWSTATEGENERATOR\|([^|]+)', response.text))

        event_validation = response.xpath('//input[@id="__EVENTVALIDATION"]/@value').get('')
        event_validation = event_validation or first(re.findall(r'__EVENTVALIDATION\|([^|]+)', response.text))

        post_data = gen_post_data(target, to_page, view_state, view_state_generator, event_validation)
        yield FormRequest(response.url, formdata=post_data, callback=self.parse)

    def detail_parse(self, response):
        d = {
            'cat_no': response.xpath('//span[@id="lblStkNo"]//text()').get(),
            'cn_name': response.xpath('//span[@id="lblProductName"]//text()').get(),
            'en_name': response.xpath('//span[@id="lblProductNameEng"]//text()').get(),
            'brand': response.xpath('//span[@id="lblBrandName"]//text()').get(),
            'cas': response.xpath('//span[@id="lblCasNo"]//text()').get(),
            'package': response.xpath('//span[@id="lblSpec"]//text()').get(),
            'unit': response.xpath('//span[@id="lblUnit"]//text()').get(),
            'price': response.xpath('//span[@id="lblPrice1"]/text()').get(),
            'delivery_time': response.xpath('//span[@id="lblTotalQtyMeo"]/text()').get(),
            'storage': response.xpath('//span[@id="lblStorageCondition"]/text()').get(),
            'prd_url': response.url,
        }
        yield AnpelItem(**d)
