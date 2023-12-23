import json
from itertools import product
from string import digits
from urllib.parse import urljoin, urlencode

from scrapy import Request

from product_spider.items import RawData, ProductPackage, SupplierProduct, RawSupplierQuotation
from product_spider.utils.items_translate import product_package_to_raw_supplier_quotation, rawdata_to_supplier_product
from product_spider.utils.json_path import json_nth_value, json_all_value
from product_spider.utils.spider_mixin import BaseSpider

default_brands = [
    {"brand_id": "0032", "alt": "ANPEL"},
    {"brand_id": "0281", "alt": "anpel-检科院"},  # 500
    {"brand_id": "B0249", "alt": "Anpel-农科院质标所"},
    {"brand_id": "402", "alt": "Anpel-国家粮食局"},
    {"brand_id": "0134", "alt": "CNW"},
    {"brand_id": "0181", "alt": "o2si"},
    # {"brand_id": "0098", "alt": "Dr"},
    # {"brand_id": "401", "alt": "DR毒素"},
    {"brand_id": "405", "alt": "安谱行政"},
    # {"brand_id": "Brands_ZG.html", "alt": "中国"},
    # {"brand_id": "Brands_KG.html", "alt": "科工委"},
    # {"brand_id": "0125", "alt": "Bepure"},
    # {"brand_id": "403", "alt": "Dr定制"},
    # {"brand_id": "0121", "alt": "Dr南京"},
    # {"brand_id": "0156", "alt": "环境保护部标准样品研究所（IERM）"},
    # {"brand_id": "0152", "alt": "农业部环境保护科研监测所 (天津)"},
    # {"brand_id": "0301", "alt": "坛墨自有"},
    # {"brand_id": "0305", "alt": "北京有色金属"},
    # {"brand_id": "0279", "alt": "海岸鸿蒙"},
    # {"brand_id": "0280", "alt": "申迪玻璃"},
    # {"brand_id": "0170", "alt": "中科美菱"},
    # {"brand_id": "399", "alt": "上海化工研究院"},
    # {"brand_id": "0302", "alt": "钢研纳克"},
    #
    # {"brand_id": "0033", "alt": "SUPELCO"},
    # {"brand_id": "0117", "alt": "TRC"},
    # {"brand_id": "0222", "alt": "Fluka"},
    # {"brand_id": "0096", "alt": "witeg"},
    # {"brand_id": "0041", "alt": "AGILENT"},
    # {"brand_id": "0039", "alt": "MERCK"},
    # {"brand_id": "0079", "alt": "BRAND"},
    # {"brand_id": "155", "alt": "Wellington"},
    # {"brand_id": "0045", "alt": "WATERS"},
    # {"brand_id": "0035", "alt": "SIGMA"},
    # {"brand_id": "0160", "alt": "Camsco"},
    # {"brand_id": "0095", "alt": "REGIS"},
    # {"brand_id": "0217", "alt": "Megazyme"},
    # {"brand_id": "Brands_C0379.html", "alt": "梯希爱(TCI)"},
    # {"brand_id": "0143", "alt": "AccuStandard"},
    # {"brand_id": "0189", "alt": "中国药品生物制品检定所"},
    # {"brand_id": "0185", "alt": "NSI"},
    # {"brand_id": "0132", "alt": "WITEGA Laboratorien"},
    # {"brand_id": "0127", "alt": "IDEX"},
    # {"brand_id": "0131", "alt": "CAMBRIDGE ISOTOP"},
    # {"brand_id": "0109", "alt": "NU-CHEK"},
    # {"brand_id": "0116", "alt": "Alfa Aesar"},
    # {"brand_id": "0049", "alt": "PALL"},
    # {"brand_id": "0050", "alt": "WHATMAN"},
    # {"brand_id": "0042", "alt": "岛津"},
    # {"brand_id": "0044", "alt": "PE"},
    # {"brand_id": "0136", "alt": "COWIE"},
    # {"brand_id": "0161", "alt": "NIST"},
    # {"brand_id": "0162", "alt": "Chiron"},
    #
    # {"brand_id": "0186", "alt": "NRCC"},
    # {"brand_id": "0196", "alt": "Thermo"},
    # {"brand_id": "0166", "alt": "Wako"},
    # {"brand_id": "0172", "alt": "TLC"},
    # {"brand_id": "0210", "alt": "亚速旺"},
    # {"brand_id": "0251", "alt": "戴安 Dionex"},
    #
    # {"brand_id": "169", "alt": "C/D/N Isotopes"},
    # {"brand_id": "170", "alt": "Cerilliant"},
    # {"brand_id": "0399", "alt": "大龙"},
    # {"brand_id": "219", "alt": "伯乐 "},
    # {"brand_id": "0184", "alt": "Hamilton"},
    # {"brand_id": "0209", "alt": "Beacon"},
    # {"brand_id": "322", "alt": "普瑞邦（Pribo）"},
    # {"brand_id": "0048", "alt": "METROHM"},
    # {"brand_id": "0091", "alt": "KNF"},
    # {"brand_id": "0081", "alt": "RESTEK"},
    # {"brand_id": "0113", "alt": "ULTRA Scientific"},
    # {"brand_id": "0114", "alt": "Phenova"},
    # {"brand_id": "0099", "alt": "USP"},
    # {"brand_id": "0066", "alt": "恒奥"},
    # {"brand_id": "0067", "alt": "津腾"},
    # {"brand_id": "0052", "alt": "SGE"},
    # {"brand_id": "0183", "alt": "Larodan"},
    # {"brand_id": "0190", "alt": "OlChemIm"},
    # {"brand_id": "0187", "alt": "MRI"},
    # {"brand_id": "0199", "alt": "RIVM"},
    # {"brand_id": "0192", "alt": "SPEX"},

    # {"brand_id": "0165", "alt": "Icon Isotope"},
    # {"brand_id": "0180", "alt": "Acros"},
    # {"brand_id": "0174", "alt": "Phytolab"},
    #
    # {"brand_id": "0157", "alt": "APSC"},
    # {"brand_id": "0158", "alt": "LGC"},
    # {"brand_id": "0159", "alt": "Medical Isotope"},
    # {"brand_id": "0146", "alt": "KARTELL "},
    # {"brand_id": "0150", "alt": "GL"},
    # {"brand_id": "0151", "alt": "Schott"},
    # {"brand_id": "359", "alt": "广州环凯"},
    # {"brand_id": "362", "alt": "青岛海博"},
    # {"brand_id": "373", "alt": "北京陆桥"},
    # {"brand_id": "397", "alt": "阿拉丁（aladdin）"},
    #
    # {"brand_id": "154", "alt": "LC LAB"},
    # {"brand_id": "0208", "alt": "上海同田生物"},
    # {"brand_id": "0201", "alt": "CanSyn"},
    # {"brand_id": "0213", "alt": "国药"},
    # {"brand_id": "0299", "alt": "Iris Biotech GmbH"},
    # {"brand_id": "0178", "alt": "Matreya LLC"},
    # {"brand_id": "Brands_A0086.html", "alt": "talboys"},
    # {"brand_id": "0191", "alt": "SIMAX"},
    # {"brand_id": "Brands_c2044.html", "alt": "DAISO"},
    # {"brand_id": "0094", "alt": "Chemservice"},
    # {"brand_id": "0036", "alt": "ALDRICH"},
    # {"brand_id": "0285", "alt": "Sigma-Aldrich"},
    # {"brand_id": "0139", "alt": "3M"},
    # {"brand_id": "0149", "alt": "VITLAB"},
    # {"brand_id": "0046", "alt": "TRANSGENOMIC"},
    # {"brand_id": "0037", "alt": "Sigma-Aldrich(原Fluka)"},
    # {"brand_id": "0059", "alt": "亚东"},
    # {"brand_id": "0804", "alt": "国家标准物质中心"},
    # {"brand_id": "0171", "alt": "林纯药"},
    # {"brand_id": "0119", "alt": "Shodex"},
    #
    # {"brand_id": "218", "alt": "艾杰尔"},
    # {"brand_id": "0167", "alt": "一恒"},
    # {"brand_id": "0115", "alt": "IRMM"},
    # {"brand_id": "0211", "alt": "Thermo Nalgene/Nunc"},
    # {"brand_id": "0085", "alt": "ORGANOMATION"},
    # {"brand_id": "0100", "alt": "ChromaDex"},
    # {"brand_id": "0034", "alt": "Sigma-Aldrich（原RDH）"},
    # {"brand_id": "0147", "alt": "艾德姆 ADAM"},
    # {"brand_id": "0254", "alt": "大连中食国实"},
    # {"brand_id": "0043", "alt": "PHENOMENEX"},
    # {"brand_id": "0080", "alt": "Eppendorf（艾本德）"},
    # {"brand_id": "0216", "alt": "Soltec Ventures"},
    # {"brand_id": "0102", "alt": "欧洲药典EPCRS"},
    # {"brand_id": "0803", "alt": "诗丹德"},
    # {"brand_id": "0177", "alt": "安亭"},
    # {"brand_id": "Brands_A.html", "alt": "锐标"},
    # {"brand_id": "0054", "alt": "SWAGELOK"},
    # {"brand_id": "0077", "alt": "泰科爱尔"},
    # {"brand_id": "0128", "alt": "Varian"},
    # {"brand_id": "Brands_B0112.html", "alt": "弗鲁克（FLUKO）"},
    # {"brand_id": "Brands_BM.html", "alt": "BM"},
    # {"brand_id": "0140", "alt": "霍尼韦尔"},
    # {"brand_id": "0224", "alt": "Honeywell"},
    # {"brand_id": "0225", "alt": "Riedel-de Haen"},
    # {"brand_id": "0145", "alt": "ISMATEC"},
    # {"brand_id": "0055", "alt": "RHEODYNE"},
    # {"brand_id": "0325", "alt": "Reagecon"},
    # {"brand_id": "0123", "alt": "Silicycle"},
    # {"brand_id": "0163", "alt": "RTC"},
    # {"brand_id": "0909", "alt": "Vetec"},
    # {"brand_id": "0118", "alt": "SLS INC."},
    # {"brand_id": "0101", "alt": "英国药典"},
    # {"brand_id": "0326", "alt": "杜邦"},
    # {"brand_id": "0223", "alt": "B&amp;J"},
    #
    # {"brand_id": "0303", "alt": "Gilian"},
    # {"brand_id": "0226", "alt": "谱育"},
    # {"brand_id": "0227", "alt": "麦克林"},
    # {"brand_id": "Brands_ABVC.html", "alt": "赫斯曼Hirschmann"},
    # {"brand_id": "404", "alt": "TRC-危险品干冰"},

    # {"brand_id": "Brands_.html", "alt": ""},

    # {"brand_id": "0133", "alt": "AS ONE CORPORATION"},
    # {"brand_id": "0051", "alt": "ORION"},
    # {"brand_id": "168", "alt": "Alexis"},
    # {"brand_id": "368", "alt": "中国检科院"},
    # {"brand_id": "0339", "alt": "芊荟化玻"},
    #
    # {"brand_id": "0252", "alt": "地球化学标准物质"},
    # {"brand_id": "0253", "alt": "CAPE"},
    # {"brand_id": "0214", "alt": "能洽"},
    # {"brand_id": "0290", "alt": "中汇"},
    # {"brand_id": "0053", "alt": "ALLTECH"},
    # {"brand_id": "0197", "alt": "Panreac"},
    # {"brand_id": "0198", "alt": "TreffLab"},
    # {"brand_id": "0200", "alt": "FAPAS"},
    # {"brand_id": "0193", "alt": "PSS"},
    # {"brand_id": "0194", "alt": "CaroteNature GmbH"},
    # {"brand_id": "0195", "alt": "Bomex"},
    # {"brand_id": "0188", "alt": "NCI"},
    # {"brand_id": "0182", "alt": "Usbio"},
    # {"brand_id": "0179", "alt": "JUN-AIR"},
    # {"brand_id": "0175", "alt": "J.T.Baker"},
    # {"brand_id": "0176", "alt": "Idexx"},
    # {"brand_id": "0173", "alt": "ChemSampCo"},
    # {"brand_id": "0138", "alt": "埃迪科技"},
    # {"brand_id": "0135", "alt": "HACH"},
    # {"brand_id": "0124", "alt": "Cole Parmer"},
    # {"brand_id": "0120", "alt": "Omnifit Ltd"},
    # {"brand_id": "0129", "alt": "东京理化"},
    # {"brand_id": "0130", "alt": "La-Pha-Pack"},
    # {"brand_id": "0141", "alt": "North"},
    # {"brand_id": "0148", "alt": "西门子SIEMENS"},
    # {"brand_id": "0078", "alt": "科瑞迈科技"},
    # {"brand_id": "0069", "alt": "依利特"},
    # {"brand_id": "0075", "alt": "福立"},
    # {"brand_id": "0056", "alt": "HYPERSIL"},
    # {"brand_id": "0058", "alt": "杰理"},
    # {"brand_id": "0060", "alt": "华鑫"},
    # {"brand_id": "0061", "alt": "联球"},
    # {"brand_id": "0062", "alt": "天章"},
    # {"brand_id": "0064", "alt": "军锐"},
    # {"brand_id": "0065", "alt": "中兴"},
    # {"brand_id": "0040", "alt": "KROMASIL"},
    # {"brand_id": "0038", "alt": "TECHWARE"},
    # {"brand_id": "0103", "alt": "MYRON L"},
    # {"brand_id": "0104", "alt": "Kou Hing Hong公司"},
    # {"brand_id": "0107", "alt": "ALFRESA"},
    # {"brand_id": "0110", "alt": "McCRONE MICROSCOPES&amp;ACCESSORIE"},
    # {"brand_id": "0092", "alt": "METTLER"},
    # {"brand_id": "0093", "alt": "VWR"},
    # {"brand_id": "0097", "alt": "CDS"},
    # {"brand_id": "0086", "alt": "天地"},
    # {"brand_id": "0087", "alt": "日本富士"},
    # {"brand_id": "0088", "alt": "MN"},
    # {"brand_id": "0089", "alt": "迪马"},
    # {"brand_id": "0090", "alt": "赛多利斯"},
    # {"brand_id": "0082", "alt": "HP"},
    # {"brand_id": "0083", "alt": "东曹TSK"},
    # {"brand_id": "0084", "alt": "UETIKON"},
    # {"brand_id": "0202", "alt": "ReseaChem"},
    # {"brand_id": "0203", "alt": "Romer Labs"},
    # {"brand_id": "0204", "alt": "Maybridge"},
    # {"brand_id": "0205", "alt": "Adamas-beta（阿达玛斯）"},
    # {"brand_id": "0206", "alt": "NSF"},
    # {"brand_id": "0207", "alt": "KAUTEX"},
    # {"brand_id": "Brands_AM.html", "alt": "AMRESCO"},
    # {"brand_id": "Brands_AX.html", "alt": "AXYGEN"},
    # {"brand_id": "Brands_A0088.html", "alt": "OHAUS"},
    # {"brand_id": "Brands_A0070.html", "alt": "inorganic veture"},
    # {"brand_id": "400", "alt": "Aalborg"},
    # {"brand_id": "398", "alt": "阿尔塔（First Standard）"},
    # {"brand_id": "Brands_QA.html", "alt": "QIAGEN"},
    # {"brand_id": "Brands_CO.html", "alt": "CORNING"},
    # {"brand_id": "Brands_EPC.html", "alt": "EPC"},
    # {"brand_id": "387", "alt": "广州洁特"},
    # {"brand_id": "Brands_A0087.html", "alt": "ENVIRONMENTAL EXPRESS"},
    # {"brand_id": "0385", "alt": "广州牧高"},
]


# TODO 破解图片验证码
class AnpelSpider(BaseSpider):
    name = "anpel"
    base_url = 'https://www.labsci.com.cn/'
    start_urls = [
        'https://www.labsci.com.cn0032',  # anpel
        # 'https://www.anpel.com.cn0134',  # cnw
        # 'https://www.anpel.com.cn0181',  # o2si
    ]

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        },
        'PROXY_POOL_REFRESH_STATUS_CODES': [403],
        'RETRY_TIMES': 20,
        'USER_AGENT': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/107.0.0.0 Safari/537.36'
        ),
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 5,
        'CONCURRENT_REQUESTS_PER_IP': 5,
    }

    def __init__(self, brands=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if brands is None:
            self.brands = default_brands
        else:
            brands = json.loads(brands)
            self.brands = brands

    def is_proxy_invalid(self, request, response):
        proxy = request.meta.get('proxy')
        if response.status in {403, }:
            self.logger.warning(f'status code:{response.status}, {request.url}')
            return True
        if "VerifyIP" in response.url:
            detected_ip = response.xpath('//span[@id="lblIP"]/text()').get()
            self.logger.warning(f"IP being detected {detected_ip}, using proxy {proxy}")
            return True
        return False

    def make_request(
            self, brand_id: str = '', brand_name: str = '', keyword: str = '',
            per_page: int = 28, page: int = 0,
            callback=None, meta: dict = None
    ):
        if meta is None:
            meta = {}
        d = {
            "SearchType": 0,
            "Keyword": keyword,
            "SkipCount": page * per_page,
            "MaxResultCount": per_page,
            "ClassId": '',
            "BrandId": brand_id,
            "BrandName": brand_name,
            "TotalQty": '',
            "PriceType": 0,
            "SortType": 4,
            "OnlyStandardVariety": True,
            "ExistTradingRecord": False,
            "CusId": '',
            "StrIfJY": "",
            "StrIfBZP": "",
            "UserLogin": "",
            "BrandType": 1,
            "nocache": 1,
        }
        return Request(
            f"https://star.labsci.com.cn/Elasticsearch/GetBrandWahStock?{urlencode(d)}",
            callback=callback,
            meta={
                "brand_id": brand_id,
                "brand_name": brand_name,
                "per_page": per_page,
                "keyword": keyword,
                "page": page + 1,
                **meta
            }
        )

    @staticmethod
    def make_search_request(
            brand_name: str = '', keyword: str = '',
            per_page: int = 28, page: int = 0,
            callback=None, meta: dict = None
    ):
        if meta is None:
            meta = {}
        d = {
            "Keyword": keyword,
            "SkipCount": per_page * page,
            "MaxResultCount": per_page,
            "ClassId": "",
            "ClassName": "全部",
            "BrandId": "",
            "BrandName": brand_name,
            "TotalQty": "全部",
            "PriceType": 0,
            "SortType": 4,
            "OnlyStandardVariety": True,
            "ExistTradingRecord": False,
            "CusId": "",
            "nocache": 1
        }
        return Request(
            f"https://star.labsci.com.cn/Elasticsearch/GetStandardWahStock?{urlencode(d)}",
            callback=callback,
            meta={
                "brand_name": brand_name,
                "per_page": per_page,
                "keyword": keyword,
                "page": page + 1,
                **meta
            }
        )

    def start_requests(self):
        # yield self.make_search_request('0032', callback=self.parse)
        for item in self.brands:
            brand_id = item.get('brand_id')
            brand_name = item.get('alt')
            if not brand_id:
                continue
            for a, b, c in product(digits, repeat=3):
                yield self.make_search_request(brand_name=brand_name, keyword=f"{a}{b}-{c}", callback=self.parse)

    def parse(self, response, **kwargs):
        j = response.json()
        rows = json_all_value(j, '$.data.items[*]')
        for row in rows:
            img = json_nth_value(row, '@.photoPath')
            prd_id = json_nth_value(row, '@.seqNoKey')
            d = {
                "brand": json_nth_value(row, '@.brandName').lower(),
                "cat_no": json_nth_value(row, '@.stkNo'),
                "chs_name": json_nth_value(row, '@.stkName'),
                "en_name": json_nth_value(row, '@.stkNameEng'),
                "cas": json_nth_value(row, '@.casNo'),
                "purity": json_nth_value(row, '@.spec'),
                "stock_info": json_nth_value(row, '@.totalQtyMeo'),

                "img_url": img and urljoin('https://dianzi.labsci.com.cn/UpFile/Brand', img.replace('\\', '/')),
                "prd_url": f"https://www.labsci.com.cn/products?id={prd_id}",
            }
            price = json_nth_value(row, '@.price')
            dd = {
                "brand": d["brand"],
                "cat_no": d["cat_no"],
                "package": json_nth_value(row, '@.specEng'),
                "currency": "RMB",
                "cost": json_nth_value(row, '@.price2') or price,
                "price": price,
                "delivery_time": json_nth_value(row, '@.totalQtyMeo'),
            }
            if d["brand"] == 'anpel':
                yield RawData(**d)
                yield ProductPackage(**dd)
            pass

            ddd = rawdata_to_supplier_product(d, self.name, self.name)
            yield SupplierProduct(**ddd)
            if dd.get("cost"):
                dddd = product_package_to_raw_supplier_quotation(d, dd, self.name, self.name)
                yield RawSupplierQuotation(**dddd)

        per_page = response.meta.get("per_page", 0)
        page = response.meta.get("page", 0)
        keyword = response.meta.get("keyword", '')
        total = json_nth_value(j, '$.data.totalCount') or 0
        if total < page * per_page:
            return
        brand_id = response.meta.get("brand_id", "")
        brand_name = response.meta.get("brand_name", "")
        yield self.make_search_request(
            brand_name=brand_name, keyword=keyword, per_page=per_page, page=page,
            callback=self.parse)
