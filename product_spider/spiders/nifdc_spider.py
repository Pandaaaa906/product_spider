import json
import re
from os import getenv
from urllib.parse import urljoin

import execjs
from scrapy import FormRequest, Request
from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.functions import strip
from product_spider.utils.items_translate import rawdata_to_supplier_product, product_package_to_raw_supplier_quotation
from product_spider.utils.parsepackage import parse_package
from product_spider.utils.spider_mixin import BaseSpider

NIFDC_USER = getenv('NIFDC_USER', '')
NIFDC_PASS = getenv('NIFDC_PASS', '')


class NifdcSpider(BaseSpider):
    name = 'nifdc'
    brand = '中检所'
    start_urls = [
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiw.do?formAction=queryzc',  # 常规
        'http://aoc.nifdc.org.cn/sell/sgoodsQuerywaiwTs.do?formAction=queryTs',  # 特殊
    ]
    code_url = 'http://aoc.nifdc.org.cn/sell/regwwuser.do?formAction=qdyanzm'
    login_url = 'http://aoc.nifdc.org.cn/sell/loginwaiw.do?formAction=index'
    password_encode_js = """var hex_chr="0123456789abcdef";function rhex(num){var str="";for(var j=0;j<=3;j++)str+=hex_chr.charAt((num>>(j*8+4))&0x0F)+hex_chr.charAt((num>>(j*8))&0x0F);return str}function str2blks_MD5(str){var nblk=((str.length+8)>>6)+1;var blks=new Array(nblk*16);for(var i=0;i<nblk*16;i++)blks[i]=0;for(i=0;i<str.length;i++)blks[i>>2]|=str.charCodeAt(i)<<((i%4)*8);blks[i>>2]|=0x80<<((i%4)*8);blks[nblk*16-2]=str.length*8;return blks}function add(x,y){return((x&0x7FFFFFFF)+(y&0x7FFFFFFF))^(x&0x80000000)^(y&0x80000000)}function rol(num,cnt){return(num<<cnt)|(num>>>(32-cnt))}function cmn(q,a,b,x,s,t){return add(rol(add(add(a,q),add(x,t)),s),b)}function ff(a,b,c,d,x,s,t){return cmn((b&c)|((~b)&d),a,b,x,s,t)}function gg(a,b,c,d,x,s,t){return cmn((b&d)|(c&(~d)),a,b,x,s,t)}function hh(a,b,c,d,x,s,t){return cmn(b^c^d,a,b,x,s,t)}function ii(a,b,c,d,x,s,t){return cmn(c^(b|(~d)),a,b,x,s,t)}function calcMD5(str){var x=str2blks_MD5(str);var a=0x67452301;var b=0xEFCDAB89;var c=0x98BADCFE;var d=0x10325476;for(var i=0;i<x.length;i+=16){var olda=a;var oldb=b;var oldc=c;var oldd=d;a=ff(a,b,c,d,x[i+0],7,0xD76AA478);d=ff(d,a,b,c,x[i+1],12,0xE8C7B756);c=ff(c,d,a,b,x[i+2],17,0x242070DB);b=ff(b,c,d,a,x[i+3],22,0xC1BDCEEE);a=ff(a,b,c,d,x[i+4],7,0xF57C0FAF);d=ff(d,a,b,c,x[i+5],12,0x4787C62A);c=ff(c,d,a,b,x[i+6],17,0xA8304613);b=ff(b,c,d,a,x[i+7],22,0xFD469501);a=ff(a,b,c,d,x[i+8],7,0x698098D8);d=ff(d,a,b,c,x[i+9],12,0x8B44F7AF);c=ff(c,d,a,b,x[i+10],17,0xFFFF5BB1);b=ff(b,c,d,a,x[i+11],22,0x895CD7BE);a=ff(a,b,c,d,x[i+12],7,0x6B901122);d=ff(d,a,b,c,x[i+13],12,0xFD987193);c=ff(c,d,a,b,x[i+14],17,0xA679438E);b=ff(b,c,d,a,x[i+15],22,0x49B40821);a=gg(a,b,c,d,x[i+1],5,0xF61E2562);d=gg(d,a,b,c,x[i+6],9,0xC040B340);c=gg(c,d,a,b,x[i+11],14,0x265E5A51);b=gg(b,c,d,a,x[i+0],20,0xE9B6C7AA);a=gg(a,b,c,d,x[i+5],5,0xD62F105D);d=gg(d,a,b,c,x[i+10],9,0x02441453);c=gg(c,d,a,b,x[i+15],14,0xD8A1E681);b=gg(b,c,d,a,x[i+4],20,0xE7D3FBC8);a=gg(a,b,c,d,x[i+9],5,0x21E1CDE6);d=gg(d,a,b,c,x[i+14],9,0xC33707D6);c=gg(c,d,a,b,x[i+3],14,0xF4D50D87);b=gg(b,c,d,a,x[i+8],20,0x455A14ED);a=gg(a,b,c,d,x[i+13],5,0xA9E3E905);d=gg(d,a,b,c,x[i+2],9,0xFCEFA3F8);c=gg(c,d,a,b,x[i+7],14,0x676F02D9);b=gg(b,c,d,a,x[i+12],20,0x8D2A4C8A);a=hh(a,b,c,d,x[i+5],4,0xFFFA3942);d=hh(d,a,b,c,x[i+8],11,0x8771F681);c=hh(c,d,a,b,x[i+11],16,0x6D9D6122);b=hh(b,c,d,a,x[i+14],23,0xFDE5380C);a=hh(a,b,c,d,x[i+1],4,0xA4BEEA44);d=hh(d,a,b,c,x[i+4],11,0x4BDECFA9);c=hh(c,d,a,b,x[i+7],16,0xF6BB4B60);b=hh(b,c,d,a,x[i+10],23,0xBEBFBC70);a=hh(a,b,c,d,x[i+13],4,0x289B7EC6);d=hh(d,a,b,c,x[i+0],11,0xEAA127FA);c=hh(c,d,a,b,x[i+3],16,0xD4EF3085);b=hh(b,c,d,a,x[i+6],23,0x04881D05);a=hh(a,b,c,d,x[i+9],4,0xD9D4D039);d=hh(d,a,b,c,x[i+12],11,0xE6DB99E5);c=hh(c,d,a,b,x[i+15],16,0x1FA27CF8);b=hh(b,c,d,a,x[i+2],23,0xC4AC5665);a=ii(a,b,c,d,x[i+0],6,0xF4292244);d=ii(d,a,b,c,x[i+7],10,0x432AFF97);c=ii(c,d,a,b,x[i+14],15,0xAB9423A7);b=ii(b,c,d,a,x[i+5],21,0xFC93A039);a=ii(a,b,c,d,x[i+12],6,0x655B59C3);d=ii(d,a,b,c,x[i+3],10,0x8F0CCC92);c=ii(c,d,a,b,x[i+10],15,0xFFEFF47D);b=ii(b,c,d,a,x[i+1],21,0x85845DD1);a=ii(a,b,c,d,x[i+8],6,0x6FA87E4F);d=ii(d,a,b,c,x[i+15],10,0xFE2CE6E0);c=ii(c,d,a,b,x[i+6],15,0xA3014314);b=ii(b,c,d,a,x[i+13],21,0x4E0811A1);a=ii(a,b,c,d,x[i+4],6,0xF7537E82);d=ii(d,a,b,c,x[i+11],10,0xBD3AF235);c=ii(c,d,a,b,x[i+2],15,0x2AD7D2BB);b=ii(b,c,d,a,x[i+9],21,0xEB86D391);a=add(a,olda);b=add(b,oldb);c=add(c,oldc);d=add(d,oldd)}return rhex(a)+rhex(b)+rhex(c)+rhex(d)}"""
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'CONCURRENT_REQUESTS_PER_IP': 2,
    }

    def start_requests(self):
        yield Request(self.code_url, callback=self.login)

    def login(self, response):
        ctx = execjs.compile(self.password_encode_js)
        password = ctx.call('calcMD5', NIFDC_PASS)
        yield FormRequest(self.login_url, formdata={
            'user_code': NIFDC_USER,
            'userpwd': password,
            'inputCode': response.text,
        }, callback=self.parse, )

    def parse(self, response, **kwargs):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        tmp = './/input[@name={!r}]/@value'
        rows = response.xpath('//table[@class="list_tab"]//tr')
        for row in rows:
            coa = row.xpath('.//td[last()]/a/@href').get()
            batch_name = row.xpath(tmp.format('xsBatch_no')).get()  # 批号
            usage = row.xpath(tmp.format('used')).get()  # 用途
            max_purchase_num = row.xpath(".//input[@name='zdgmshu']/parent::td/text()").get()  # 最大购买数量
            prd_attrs = json.dumps({
                "usage": usage,
                "max_purchase_num": strip(max_purchase_num),
            })
            d = {
                'brand': self.brand,
                'cat_no': (cat_no := row.xpath(tmp.format('sgoods_no')).get()),
                'parent': row.xpath(tmp.format('sgoods_type')).get(),
                'chs_name': row.xpath(tmp.format('sgoods_name')).get(),
                'en_name': row.xpath(tmp.format('english_name')).get(),
                'info2': row.xpath(tmp.format('save_condition')).get(),
                'stock_info': row.xpath(tmp.format('zdgmshu')).get(),
                'prd_url': coa and urljoin(response.url, coa),
                "attrs": prd_attrs,
            }
            yield RawData(**d)
            package_attrs = json.dumps({
                "batch_name": batch_name,
            })
            package = parse_package(row.xpath(tmp.format('standard')).get())
            dd = {
                'brand': self.brand,
                'cat_no': cat_no,
                'package': package,
                'cost': row.xpath(tmp.format('unit_price')).get(),
                'info': row.xpath(tmp.format('xsBatch_no')).get(),
                'stock_num': row.xpath(tmp.format('zdgmshu')).get(),
                'currency': 'RMB',
                "attrs": package_attrs,
            }
            yield ProductPackage(**dd)
            ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
            dddd = product_package_to_raw_supplier_quotation(d, dd, platform=self.name, vendor=self.name)

            yield SupplierProduct(**ddd)
            yield RawSupplierQuotation(**dddd)

        m = re.search(r'(?:buildPageCtrlOne001\()(\d+),(\d+),(\d+)', response.text)
        if not m:
            return
        cur_page, per_page, total = m.groups()
        if (cur_page := int(cur_page)) * int(per_page) > int(total):
            return
        form_data = {
            "curPage": str(cur_page + 1),
            "toPage": str(cur_page),
        }
        yield FormRequest(response.url, formdata=form_data, callback=self.parse_list)
