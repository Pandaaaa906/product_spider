import re
import time
from html import unescape
from urllib.parse import urljoin

from more_itertools import first
from scrapy import Request, FormRequest

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
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


brands_urls = [
    # {"href": "Brands_0032.html", "alt": "ANPEL"},
    # {"href": "Brands_0281.html", "alt": "anpel-检科院"},   # 500
    {"href": "Brands_B0249.html", "alt": "Anpel-农科院质标所"},
    {"href": "Brands_402.html", "alt": "Anpel-国家粮食局"},
    # {"href": "Brands_0134.html", "alt": "CNW"},
    # {"href": "Brands_0181.html", "alt": "o2si"},
    # {"href": "Brands_0098.html", "alt": "Dr"},
    {"href": "Brands_401.html", "alt": "DR毒素"},
    {"href": "Brands_405.html", "alt": "安谱行政"},
    {"href": "Brands_ZG.html", "alt": "中国"},
    {"href": "Brands_KG.html", "alt": "科工委"},
    {"href": "Brands_0125.html", "alt": "Bepure"},
    {"href": "Brands_403.html", "alt": "Dr定制"},
    {"href": "Brands_0121.html", "alt": "Dr南京"},
    {"href": "Brands_0156.html", "alt": "环境保护部标准样品研究所（IERM）"},
    {"href": "Brands_0152.html", "alt": "农业部环境保护科研监测所 (天津)"},
    {"href": "Brands_0301.html", "alt": "坛墨自有"},
    {"href": "Brands_0305.html", "alt": "北京有色金属"},
    {"href": "Brands_0279.html", "alt": "海岸鸿蒙"},
    {"href": "Brands_0280.html", "alt": "申迪玻璃"},
    {"href": "Brands_0170.html", "alt": "中科美菱"},
    {"href": "Brands_399.html", "alt": "上海化工研究院"},
    {"href": "Brands_0302.html", "alt": "钢研纳克"},

    {"href": "Brands_0033.html", "alt": "SUPELCO"},
    # {"href": "Brands_0117.html", "alt": "TRC"},
    {"href": "Brands_0222.html", "alt": "Fluka"},
    {"href": "Brands_0096.html", "alt": "witeg"},
    {"href": "Brands_0041.html", "alt": "AGILENT"},
    # {"href": "Brands_0039.html", "alt": "MERCK"},
    # {"href": "Brands_0079.html", "alt": "BRAND"},
    {"href": "Brands_155.html", "alt": "Wellington"},
    {"href": "Brands_0045.html", "alt": "WATERS"},
    # {"href": "Brands_0035.html", "alt": "SIGMA"},
    {"href": "Brands_0160.html", "alt": "Camsco"},
    {"href": "Brands_0095.html", "alt": "REGIS"},
    {"href": "Brands_0217.html", "alt": "Megazyme"},
    {"href": "Brands_C0379.html", "alt": "梯希爱(TCI)"},
    {"href": "Brands_0143.html", "alt": "AccuStandard"},
    # {"href": "Brands_0189.html", "alt": "中国药品生物制品检定所"},
    {"href": "Brands_0185.html", "alt": "NSI"},
    {"href": "Brands_0132.html", "alt": "WITEGA Laboratorien"},
    {"href": "Brands_0127.html", "alt": "IDEX"},
    {"href": "Brands_0131.html", "alt": "CAMBRIDGE ISOTOP"},
    {"href": "Brands_0109.html", "alt": "NU-CHEK"},
    {"href": "Brands_0116.html", "alt": "Alfa Aesar"},
    {"href": "Brands_0049.html", "alt": "PALL"},
    {"href": "Brands_0050.html", "alt": "WHATMAN"},
    {"href": "Brands_0042.html", "alt": "岛津"},
    {"href": "Brands_0044.html", "alt": "PE"},
    {"href": "Brands_0136.html", "alt": "COWIE"},
    {"href": "Brands_0161.html", "alt": "NIST"},
    {"href": "Brands_0162.html", "alt": "Chiron"},

    {"href": "Brands_0186.html", "alt": "NRCC"},
    {"href": "Brands_0196.html", "alt": "Thermo"},
    {"href": "Brands_0166.html", "alt": "Wako"},
    # {"href": "Brands_0172.html", "alt": "TLC"},
    {"href": "Brands_0210.html", "alt": "亚速旺"},
    {"href": "Brands_0251.html", "alt": "戴安 Dionex"},

    {"href": "Brands_169.html", "alt": "C/D/N Isotopes"},
    {"href": "Brands_170.html", "alt": "Cerilliant"},
    # {"href": "Brands_0399.html", "alt": "大龙"},
    {"href": "Brands_219.html", "alt": "伯乐 "},
    {"href": "Brands_0184.html", "alt": "Hamilton"},
    {"href": "Brands_0209.html", "alt": "Beacon"},
    {"href": "Brands_322.html", "alt": "普瑞邦（Pribo）"},
    {"href": "Brands_0048.html", "alt": "METROHM"},
    {"href": "Brands_0091.html", "alt": "KNF"},
    {"href": "Brands_0081.html", "alt": "RESTEK"},
    {"href": "Brands_0113.html", "alt": "ULTRA Scientific"},
    {"href": "Brands_0114.html", "alt": "Phenova"},
    {"href": "Brands_0099.html", "alt": "USP"},
    {"href": "Brands_0066.html", "alt": "恒奥"},
    {"href": "Brands_0067.html", "alt": "津腾"},
    {"href": "Brands_0052.html", "alt": "SGE"},
    {"href": "Brands_0183.html", "alt": "Larodan"},
    {"href": "Brands_0190.html", "alt": "OlChemIm"},
    {"href": "Brands_0187.html", "alt": "MRI"},
    {"href": "Brands_0199.html", "alt": "RIVM"},
    {"href": "Brands_0192.html", "alt": "SPEX"},

    {"href": "Brands_0165.html", "alt": "Icon Isotope"},
    {"href": "Brands_0180.html", "alt": "Acros"},
    {"href": "Brands_0174.html", "alt": "Phytolab"},

    {"href": "Brands_0157.html", "alt": "APSC"},
    # {"href": "Brands_0158.html", "alt": "LGC"},
    {"href": "Brands_0159.html", "alt": "Medical Isotope"},
    {"href": "Brands_0146.html", "alt": "KARTELL "},
    {"href": "Brands_0150.html", "alt": "GL"},
    {"href": "Brands_0151.html", "alt": "Schott"},
    {"href": "Brands_359.html", "alt": "广州环凯"},
    {"href": "Brands_362.html", "alt": "青岛海博"},
    {"href": "Brands_373.html", "alt": "北京陆桥"},
    {"href": "Brands_397.html", "alt": "阿拉丁（aladdin）"},

    {"href": "Brands_154.html", "alt": "LC LAB"},
    {"href": "Brands_0208.html", "alt": "上海同田生物"},
    {"href": "Brands_0201.html", "alt": "CanSyn"},
    {"href": "Brands_0213.html", "alt": "国药"},
    {"href": "Brands_0299.html", "alt": "Iris Biotech GmbH"},
    {"href": "Brands_0178.html", "alt": "Matreya LLC"},
    {"href": "Brands_A0086.html", "alt": "talboys"},
    {"href": "Brands_0191.html", "alt": "SIMAX"},
    {"href": "Brands_c2044.html", "alt": "DAISO"},
    {"href": "Brands_0094.html", "alt": "Chemservice"},
    {"href": "Brands_0036.html", "alt": "ALDRICH"},
    {"href": "Brands_0285.html", "alt": "Sigma-Aldrich"},
    {"href": "Brands_0139.html", "alt": "3M"},
    {"href": "Brands_0149.html", "alt": "VITLAB"},
    {"href": "Brands_0046.html", "alt": "TRANSGENOMIC"},
    {"href": "Brands_0037.html", "alt": "Sigma-Aldrich(原Fluka)"},
    {"href": "Brands_0059.html", "alt": "亚东"},
    {"href": "Brands_0804.html", "alt": "国家标准物质中心"},
    {"href": "Brands_0171.html", "alt": "林纯药"},
    {"href": "Brands_0119.html", "alt": "Shodex"},

    {"href": "Brands_218.html", "alt": "艾杰尔"},
    {"href": "Brands_0167.html", "alt": "一恒"},
    {"href": "Brands_0115.html", "alt": "IRMM"},
    {"href": "Brands_0211.html", "alt": "Thermo Nalgene/Nunc"},
    {"href": "Brands_0085.html", "alt": "ORGANOMATION"},
    {"href": "Brands_0100.html", "alt": "ChromaDex"},
    {"href": "Brands_0034.html", "alt": "Sigma-Aldrich（原RDH）"},
    {"href": "Brands_0147.html", "alt": "艾德姆 ADAM"},
    {"href": "Brands_0254.html", "alt": "大连中食国实"},
    {"href": "Brands_0043.html", "alt": "PHENOMENEX"},
    {"href": "Brands_0080.html", "alt": "Eppendorf（艾本德）"},
    {"href": "Brands_0216.html", "alt": "Soltec Ventures"},
    {"href": "Brands_0102.html", "alt": "欧洲药典EPCRS"},
    {"href": "Brands_0803.html", "alt": "诗丹德"},
    {"href": "Brands_0177.html", "alt": "安亭"},
    {"href": "Brands_A.html", "alt": "锐标"},
    {"href": "Brands_0054.html", "alt": "SWAGELOK"},
    {"href": "Brands_0077.html", "alt": "泰科爱尔"},
    {"href": "Brands_0128.html", "alt": "Varian"},
    {"href": "Brands_B0112.html", "alt": "弗鲁克（FLUKO）"},
    {"href": "Brands_BM.html", "alt": "BM"},
    {"href": "Brands_0140.html", "alt": "霍尼韦尔"},
    {"href": "Brands_0224.html", "alt": "Honeywell"},
    {"href": "Brands_0225.html", "alt": "Riedel-de Haen"},
    {"href": "Brands_0145.html", "alt": "ISMATEC"},
    {"href": "Brands_0055.html", "alt": "RHEODYNE"},
    {"href": "Brands_0325.html", "alt": "Reagecon"},
    {"href": "Brands_0123.html", "alt": "Silicycle"},
    {"href": "Brands_0163.html", "alt": "RTC"},
    {"href": "Brands_0909.html", "alt": "Vetec"},
    {"href": "Brands_0118.html", "alt": "SLS INC."},
    # {"href": "Brands_0101.html", "alt": "英国药典"},
    {"href": "Brands_0326.html", "alt": "杜邦"},
    {"href": "Brands_0223.html", "alt": "B&amp;J"},

    {"href": "Brands_0303.html", "alt": "Gilian"},
    {"href": "Brands_0226.html", "alt": "谱育"},
    {"href": "Brands_0227.html", "alt": "麦克林"},
    {"href": "Brands_ABVC.html", "alt": "赫斯曼Hirschmann"},
    {"href": "Brands_404.html", "alt": "TRC-危险品干冰"},

    # {"href": "Brands_.html", "alt": ""},

    {"href": "Brands_0133.html", "alt": "AS ONE CORPORATION"},
    {"href": "Brands_0051.html", "alt": "ORION"},
    {"href": "Brands_168.html", "alt": "Alexis"},
    {"href": "Brands_368.html", "alt": "中国检科院"},
    {"href": "Brands_0339.html", "alt": "芊荟化玻"},

    {"href": "Brands_0252.html", "alt": "地球化学标准物质"},
    {"href": "Brands_0253.html", "alt": "CAPE"},
    {"href": "Brands_0214.html", "alt": "能洽"},
    {"href": "Brands_0290.html", "alt": "中汇"},
    {"href": "Brands_0053.html", "alt": "ALLTECH"},
    {"href": "Brands_0197.html", "alt": "Panreac"},
    {"href": "Brands_0198.html", "alt": "TreffLab"},
    {"href": "Brands_0200.html", "alt": "FAPAS"},
    {"href": "Brands_0193.html", "alt": "PSS"},
    {"href": "Brands_0194.html", "alt": "CaroteNature GmbH"},
    {"href": "Brands_0195.html", "alt": "Bomex"},
    {"href": "Brands_0188.html", "alt": "NCI"},
    {"href": "Brands_0182.html", "alt": "Usbio"},
    {"href": "Brands_0179.html", "alt": "JUN-AIR"},
    {"href": "Brands_0175.html", "alt": "J.T.Baker"},
    {"href": "Brands_0176.html", "alt": "Idexx"},
    {"href": "Brands_0173.html", "alt": "ChemSampCo"},
    {"href": "Brands_0138.html", "alt": "埃迪科技"},
    {"href": "Brands_0135.html", "alt": "HACH"},
    {"href": "Brands_0124.html", "alt": "Cole Parmer"},
    {"href": "Brands_0120.html", "alt": "Omnifit Ltd"},
    {"href": "Brands_0129.html", "alt": "东京理化"},
    {"href": "Brands_0130.html", "alt": "La-Pha-Pack"},
    {"href": "Brands_0141.html", "alt": "North"},
    {"href": "Brands_0148.html", "alt": "西门子SIEMENS"},
    {"href": "Brands_0078.html", "alt": "科瑞迈科技"},
    {"href": "Brands_0069.html", "alt": "依利特"},
    {"href": "Brands_0075.html", "alt": "福立"},
    {"href": "Brands_0056.html", "alt": "HYPERSIL"},
    {"href": "Brands_0058.html", "alt": "杰理"},
    {"href": "Brands_0060.html", "alt": "华鑫"},
    {"href": "Brands_0061.html", "alt": "联球"},
    {"href": "Brands_0062.html", "alt": "天章"},
    {"href": "Brands_0064.html", "alt": "军锐"},
    {"href": "Brands_0065.html", "alt": "中兴"},
    {"href": "Brands_0040.html", "alt": "KROMASIL"},
    {"href": "Brands_0038.html", "alt": "TECHWARE"},
    {"href": "Brands_0103.html", "alt": "MYRON L"},
    {"href": "Brands_0104.html", "alt": "Kou Hing Hong公司"},
    {"href": "Brands_0107.html", "alt": "ALFRESA"},
    {"href": "Brands_0110.html", "alt": "McCRONE MICROSCOPES&amp;ACCESSORIE"},
    {"href": "Brands_0092.html", "alt": "METTLER"},
    {"href": "Brands_0093.html", "alt": "VWR"},
    {"href": "Brands_0097.html", "alt": "CDS"},
    {"href": "Brands_0086.html", "alt": "天地"},
    {"href": "Brands_0087.html", "alt": "日本富士"},
    {"href": "Brands_0088.html", "alt": "MN"},
    {"href": "Brands_0089.html", "alt": "迪马"},
    {"href": "Brands_0090.html", "alt": "赛多利斯"},
    {"href": "Brands_0082.html", "alt": "HP"},
    {"href": "Brands_0083.html", "alt": "东曹TSK"},
    {"href": "Brands_0084.html", "alt": "UETIKON"},
    {"href": "Brands_0202.html", "alt": "ReseaChem"},
    {"href": "Brands_0203.html", "alt": "Romer Labs"},
    {"href": "Brands_0204.html", "alt": "Maybridge"},
    {"href": "Brands_0205.html", "alt": "Adamas-beta（阿达玛斯）"},
    {"href": "Brands_0206.html", "alt": "NSF"},
    {"href": "Brands_0207.html", "alt": "KAUTEX"},
    {"href": "Brands_AM.html", "alt": "AMRESCO"},
    {"href": "Brands_AX.html", "alt": "AXYGEN"},
    {"href": "Brands_A0088.html", "alt": "OHAUS"},
    {"href": "Brands_A0070.html", "alt": "inorganic veture"},
    {"href": "Brands_400.html", "alt": "Aalborg"},
    {"href": "Brands_398.html", "alt": "阿尔塔（First Standard）"},
    {"href": "Brands_QA.html", "alt": "QIAGEN"},
    {"href": "Brands_CO.html", "alt": "CORNING"},
    {"href": "Brands_EPC.html", "alt": "EPC"},
    {"href": "Brands_387.html", "alt": "广州洁特"},
    {"href": "Brands_A0087.html", "alt": "ENVIRONMENTAL EXPRESS"},
    {"href": "Brands_0385.html", "alt": "广州牧高"},
]


# TODO 破解图片验证码
class AnpelSpider(BaseSpider):
    name = "anpel"
    base_url = 'https://www.labsci.com.cn/'
    start_urls = [
        'https://www.labsci.com.cn/Brands_0032.html',  # anpel
        # 'https://www.anpel.com.cn/Brands_0134.html',  # cnw
        # 'https://www.anpel.com.cn/Brands_0181.html',  # o2si
    ]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'RETRY_HTTP_CODES': [403],
        'RETRY_TIMES': 10,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        ),
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 5,
        'CONCURRENT_REQUESTS_PER_IP': 5,
    }

    def is_proxy_invalid(self, request, response):
        if response.status in {403, }:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        return False

    def start_requests(self):
        for item in brands_urls:
            url = item.get('href')
            brand = (tmp := item.get('alt')) and unescape(tmp)
            if not brand:
                continue
            yield Request(urljoin(self.base_url, url), callback=self.parse, meta={'sub_brand': brand})

    def parse(self, response, *args, **kwargs):
        rel_urls = response.xpath('//a[@class="Stkno"]/@href').extract()
        for rel_url in rel_urls:
            yield Request(
                urljoin(self.base_url, rel_url), callback=self.detail_parse,
                meta={'sub_brand': response.meta.get('sub_brand')}
            )

        next_page = response.xpath('//a[contains(@style,"background-color:#0088FF;")]/../following-sibling::td/a')
        if not next_page:
            return
        target = next_page.xpath('./@id').get()
        to_page = next_page.xpath('./text()').get()

        view_state = response.xpath('//input[@id="__VIEWSTATE"]/@value').get('')
        view_state = view_state or first(re.findall(r'__VIEWSTATE\|([^|]+)', response.text))

        view_state_generator = response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get('')
        view_state_generator = view_state_generator or first(
            re.findall(r'__VIEWSTATEGENERATOR\|([^|]+)', response.text))

        event_validation = response.xpath('//input[@id="__EVENTVALIDATION"]/@value').get('')
        event_validation = event_validation or first(re.findall(r'__EVENTVALIDATION\|([^|]+)', response.text))

        post_data = gen_post_data(target, to_page, view_state, view_state_generator, event_validation)
        yield FormRequest(
            response.url, formdata=post_data, callback=self.parse, meta={'sub_brand': response.meta.get('sub_brand')}
        )

    def detail_parse(self, response):
        time.sleep(10)
        sub_brand = response.meta.get('sub_brand')
        cat_no = response.xpath('//span[@id="lblStkNo"]//text()').get()
        cn_name = response.xpath('//span[@id="lblProductName"]//text()').get()
        en_name = response.xpath('//span[@id="lblProductNameEng"]//text()').get()
        cas = response.xpath('//span[@id="lblCasNo"]//text()').get()
        package = response.xpath('//span[@id="lblSpec"]//text()').get()
        unit = response.xpath('//span[@id="lblUnit"]//text()').get()
        cost = response.xpath('//span[@id="lblPrice1"]/text()').get()
        delivery_time = response.xpath('//span[@id="lblTotalQtyMeo"]/text()').get()
        storage = response.xpath('//span[@id="lblStorageCondition"]/text()').get()

        if sub_brand == 'ANPEL':
            d = {
                "brand": self.name,
                "cat_no": cat_no,
                "cn_name": cn_name,
                "en_name": en_name,
                "cas": cas,
                "delivery_time": delivery_time,
                "storage": storage,
                "prd_url": response.url,
            }
            dd = {
                "brand": self.name,
                "cat_no": cat_no,
                "package": package,
                "cost": cost,
                "currency": 'RMB',
            }
            yield RawData(**d)
            yield ProductPackage(**dd)

        ddd = {
            "platform": sub_brand,
            "brand": sub_brand,
            "vendor": sub_brand,
            'cat_no': cat_no,
            "source_id": f'{self.name}_{cat_no}_{package}',
            'chs_name': cn_name,
            'en_name': en_name,
            'cas': cas,
            'package': package,
            'cost': cost,
            "delivery": delivery_time,
            'storage_condition': storage,
            'prd_url': response.url,
            "currency": "RMB",
        }
        dddd = {
            "platform": sub_brand,
            "brand": sub_brand,
            "vendor": sub_brand,
            "source_id": f'{self.name}_{cat_no}',
            'cat_no': cat_no,
            'package': package,
            'discount_price': cost,
            'price': cost,
            'cas': cas,
            'delivery': delivery_time,
            'currency': "RMB",
        }
        yield SupplierProduct(**ddd)
        yield RawSupplierQuotation(**dddd)
