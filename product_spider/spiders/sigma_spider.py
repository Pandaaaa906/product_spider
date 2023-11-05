import json
import re
from datetime import datetime
from html import unescape
from typing import List
from urllib.parse import urljoin

from jsonpath_ng.ext import parse
from more_itertools import first, nth
from scrapy import Request
from scrapy.http.request.json_request import JsonRequest

from items import RawSupplierQuotation
from product_spider.items import RawData, ProductPackage
from product_spider.utils.functions import dumps
from product_spider.utils.spider_mixin import BaseSpider

IGNORE_BRANDS = {
    'cerillian'
}
BRANDS_MAPPING = {
    "sigald": "sigma",
    "sial": "sigma",
    "aldrich": "sigma",
    "sigma": "sigma",
    "mm": "supelco",
}


class SigmaSpider(BaseSpider):
    name = "sigma"
    start_urls = ["https://www.sigmaaldrich.cn/CN/zh", ]
    base_url = "https://www.sigmaaldrich.com/"
    api_url = "https://www.sigmaaldrich.cn/api"
    api_headers = {
        'X-Gql-Access-Token': 'f5045013-7888-11ee-8389-b5bd1b960edc',
        'X-Gql-Blue-Erp-Enabled': 'true',
        'X-Gql-Country': 'CN',
        'X-Gql-Language': 'zh',

    }

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) '
                          'AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8',
            'Accept-Encoding': 'gzip, deflate, br', 'Accept': '*/*', 'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        },
        # "DOWNLOADER_MIDDLEWARES": {
        #     'product_spider.middlewares.proxy_middlewares.RandomProxyMiddleWare': 543,
        # },
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'CONCURRENT_REQUESTS_PER_IP': 4,
    }
    
    def __init__(self, *args, per_page: int = 1000, **kwargs):
        self.per_page = per_page
        super().__init__(*args, **kwargs)

    def make_search_request(self, facets: List[str], *, callback, page=1, per_page: int = None, meta: dict = None):
        if per_page is None:
            per_page = self.per_page
        if meta is None:
            meta = {}
        selected_facets = [{"key": f[0], "options": f[1].split(',')} for facet in facets if (f := facet.split(':'))]
        return JsonRequest(
            self.api_url,
            data={
                "operationName": "CategoryProductSearch",
                "variables": {
                    "searchTerm": None,
                    "page": page,
                    "perPage": per_page,
                    "sort": "relevance",
                    "selectedFacets": selected_facets,
                    "facetSet": [
                        "facet_product_category",
                        "facet_fwght",
                        "facet_web_functgp",
                        "facet_web_greener_alternative_principles",
                        "facet_web_markush_class",
                        "facet_web_markush_group",
                        "facet_melting_point",
                        "facet_ph_val",
                        "facet_physical_form",
                        "facet_product_category",
                        "facet_web_react_suitability_reaction_type",
                        "facet_web_react_suitability_reagent_type",
                        "facet_shipping",
                        "facet_brand"
                    ]
                },
                "query": "query CategoryProductSearch($searchTerm: String, $page: Int!, $perPage: Int!, $sort: Sort, $selectedFacets: [FacetInput!], $facetSet: [String]) {\n  getProductSearchResults(input: {searchTerm: $searchTerm, pagination: {page: $page, perPage: $perPage}, sort: $sort, group: product, facets: $selectedFacets, facetSet: $facetSet}) {\n    ...CategoryProductSearchFields\n    __typename\n  }\n}\n\nfragment CategoryProductSearchFields on ProductSearchResults {\n  metadata {\n    itemCount\n    page\n    perPage\n    numPages\n    __typename\n  }\n  items {\n    ... on Product {\n      ...CategorySubstanceProductFields\n      __typename\n    }\n    __typename\n  }\n  facets {\n    key\n    numToDisplay\n    isHidden\n    isCollapsed\n    multiSelect\n    prefix\n    options {\n      value\n      count\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CategorySubstanceProductFields on Product {\n  name\n  displaySellerName\n  productNumber\n  productKey\n  isMarketplace\n  marketplaceOfferId\n  marketplaceSellerId\n  attributes {\n    key\n    label\n    values\n    __typename\n  }\n  brand {\n    key\n    erpKey\n    name\n    color\n    __typename\n  }\n  images {\n    altText\n    smallUrl\n    mediumUrl\n    largeUrl\n    __typename\n  }\n  description\n  paMessage\n  __typename\n}\n"
            },
            meta={
                "facets": facets,
                **meta
            },
            headers={
                **self.api_headers,
                'X-Gql-Operation-Name': 'CategoryProductSearch',
            },
            callback=callback
        )

    def make_price_request(
            self,
            brand, catalog_type: str, product_key, product_number, material_ids: List[str],
            *, callback, meta: dict = None
    ):
        if meta is None:
            meta = {}
        return JsonRequest(
            self.api_url,
            data={
                "operationName": "PricingAndAvailability",
                "query": "query PricingAndAvailability($productNumber: String!, $brand: String, $quantity: Int!, $catalogType: CatalogType, $checkForPb: Boolean, $orgId: String, $materialIds: [String!], $displaySDS: Boolean = false, $dealerId: String, $checkBuyNow: Boolean, $productKey: String, $erp_type: [String!]) {\n  getPricingForProduct(input: {productNumber: $productNumber, brand: $brand, quantity: $quantity, catalogType: $catalogType, checkForPb: $checkForPb, orgId: $orgId, materialIds: $materialIds, dealerId: $dealerId, checkBuyNow: $checkBuyNow, productKey: $productKey, erp_type: $erp_type}) {\n    ...ProductPricingDetail\n    __typename\n  }\n}\n\nfragment ProductPricingDetail on ProductPricing {\n  dealerId\n  productNumber\n  country\n  materialPricing {\n    ...ValidMaterialPricingDetail\n    __typename\n  }\n  discontinuedPricingInfo {\n    ...DiscontinuedMaterialPricingDetail\n    __typename\n  }\n  dchainMessage\n  productInfo {\n    ...ProductInfoMessageDetail\n    __typename\n  }\n  __typename\n}\n\nfragment ValidMaterialPricingDetail on ValidMaterialPricing {\n  brand\n  type\n  currency\n  dealerId\n  listPriceCurrency\n  listPrice\n  shipsToday\n  freeFreight\n  sdsLanguages\n  catalogType\n  marketplaceOfferId\n  marketplaceSellerId\n  materialDescription\n  materialNumber\n  materialId\n  netPrice\n  packageSize\n  packageType\n  price\n  isBuyNow\n  product\n  productGroupSBU\n  quantity\n  isPBAvailable\n  vendorSKU\n  isBlockedProduct\n  hidePriceMessageKey\n  expirationDate\n  availableQtyInStock\n  availabilities {\n    ...Availabilities\n    __typename\n  }\n  additionalInfo {\n    ...AdditionalInfo\n    __typename\n  }\n  promotionalMessage {\n    ...PromotionalMessage\n    __typename\n  }\n  ... @include(if: $displaySDS) {\n    sdsLanguages\n    __typename\n  }\n  minOrderQuantity\n  __typename\n}\n\nfragment Availabilities on MaterialAvailability {\n  date\n  key\n  plantLoc\n  quantity\n  displayFromLink\n  displayInquireLink\n  messageType\n  contactInfo {\n    contactPhone\n    contactEmail\n    __typename\n  }\n  availabilityOverwriteMessage {\n    messageKey\n    messageValue\n    messageVariable1\n    messageVariable2\n    messageVariable3\n    __typename\n  }\n  supplementaryMessage {\n    messageKey\n    messageValue\n    messageVariable1\n    messageVariable2\n    messageVariable3\n    __typename\n  }\n  __typename\n}\n\nfragment AdditionalInfo on CartAdditionalInfo {\n  carrierRestriction\n  unNumber\n  tariff\n  casNumber\n  jfcCode\n  pdcCode\n  __typename\n}\n\nfragment PromotionalMessage on PromotionalMessage {\n  messageKey\n  messageValue\n  messageVariable1\n  messageVariable2\n  messageVariable3\n  __typename\n}\n\nfragment DiscontinuedMaterialPricingDetail on DiscontinuedMaterialPricing {\n  errorMsg\n  paramList\n  hideReplacementProductLink\n  displaySimilarProductLabel\n  hideTechnicalServiceLink\n  replacementProducts {\n    ...ReplacementProductDetail\n    __typename\n  }\n  alternateMaterials {\n    ...AlternateMaterialDetail\n    __typename\n  }\n  __typename\n}\n\nfragment ReplacementProductDetail on Product {\n  productNumber\n  name\n  description\n  sdsLanguages\n  images {\n    mediumUrl\n    altText\n    __typename\n  }\n  brand {\n    key\n    erpKey\n    name\n    logo {\n      smallUrl\n      altText\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment AlternateMaterialDetail on Material {\n  number\n  __typename\n}\n\nfragment ProductInfoMessageDetail on ProductInfoMessage {\n  productNumber\n  messageType\n  message\n  __typename\n}\n",
                "variables": {
                    "brand": brand,
                    "catalogType": catalog_type,
                    "checkBuyNow": True,
                    "checkForPb": True,
                    "dealerId": "",
                    "displaySDS": False,
                    "erp_type": [
                        "red"
                    ],
                    "materialIds": material_ids,
                    "orgId": None,
                    "productKey": product_key,
                    "productNumber": product_number,
                    "quantity": 1
                }
            },
            headers={
                **self.api_headers,
                'X-Gql-Operation-Name': 'PricingAndAvailability',
            },
            callback=callback,
            meta={**meta}
        )

    @staticmethod
    def _get_next_data(response):
        t = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
        return json.loads(t)

    @staticmethod
    def _nth_value(d: dict, p: str, n=1):
        ret = (m := nth(parse(p).find(d), n, None)) and m.value
        if isinstance(ret, str):
            return unescape(ret)
        return ret

    def parse(self, response, **kwargs):
        j = self._get_next_data(response)
        rel_urls = (v.value for v in parse('$..*[?menuItem=false].url').find(j))
        for rel_url in rel_urls:
            if '/products/' not in rel_url:
                continue
            # TODO should be a better way to filter which url will be crawl
            if 'chemistry-and-biochemicals' not in rel_url:
                continue
            yield Request(urljoin(self.base_url, rel_url), callback=self.parse_category_page)
        pass

    def parse_category_page(self, response):
        j = self._get_next_data(response)
        facets = first(parse('$..categorysearchresult.facets').find(j), None)
        if not facets:
            return
        yield self.make_search_request(
            facets.value,
            callback=self.parse_list
        )

    def parse_list(self, response):
        j = json.loads(response.text)
        rows = parse('$..getProductSearchResults.items[*]').find(j)
        for row in rows:
            brand = (m := first(parse('@.brand.erpKey').find(row), None)) and m.value
            cat_no = (m := first(parse('@.productKey').find(row), None)) and m.value
            yield Request(
                f'https://www.sigmaaldrich.cn/CN/zh/product/{brand}/{cat_no}',
                callback=self.parse_detail,
            )


        # next_page
        page = (m := first(parse('$..metadata.page').find(json.loads(response.text)), None)) and m.value
        total_page = (m := first(parse('$..metadata.numPages').find(json.loads(response.text)), None)) and m.value
        if not page or not total_page:
            return
        if total_page <= page:
            return
        facets = response.meta.get("facets")
        yield self.make_search_request(
            facets,
            callback=self.parse_list,
            page=page+1
        )

    def parse_detail(self, response):
        j = self._get_next_data(response)
        rel_img = (m := first(parse('$..data.getProductDetail.images[0].largeUrl').find(j), None)) and m.value
        brand = (m := first(parse('$..data.getProductDetail.brand.erpKey').find(j), None)) and m.value
        cat_no = (m := first(parse('$..data.getProductDetail.productNumber').find(j), None)) and m.value
        prd_key = (m := first(parse('$..data.getProductDetail.productKey').find(j), None)) and m.value
        catalog_id = (m := first(parse('$..data.getProductDetail.catalogId').find(j), None)) and m.value
        material_ids = (m := first(parse('$..data.getProductDetail.materialIds').find(j), None)) and m.value
        mf = (m := first(parse('$..data.getProductDetail.empiricalFormula').find(j), None)) and m.value
        if isinstance(mf, str):
            mf = re.sub('</?[^>]+>', '', mf)
        if not brand:
            self.logger.warning(f"no brand found in url: {response.url}")
            return
        if (brand := brand.lower()) not in BRANDS_MAPPING:
            self.logger.warning(f"brand {brand!r} not found in BRANDS_MAPPING: {response.url}")
        attrs = {
            "ph": self._nth_value(j, '$..data.getProductDetail.attributes[?@.key="ph value.default"].values[0]'),
            "boiling_point": self._nth_value(j, '$..data.getProductDetail.attributes[?@.key="boiling point.default"].values[0]'),
            "density": self._nth_value(j, '$..data.getProductDetail.attributes[?@.key="density.default"].values[0]'),
            "solubility": self._nth_value(j, '$..data.getProductDetail.attributes[?@.key="solubility.default"].values[0]'),
            "flash_point": self._nth_value(j, '$..data.getProductDetail.compliance[?@.key="flash_point_c"].value'),
        }
        d = {
            "brand": BRANDS_MAPPING.get(brand, brand),
            "cat_no": cat_no,
            "chs_name": self._nth_value(j, '$..data.getProductDetail.name'),
            "cas": self._nth_value(j, '$..data.getProductDetail.casNumber'),
            "mw": self._nth_value(j, '$..data.getProductDetail.molecularWeight'),
            "mf": mf,
            "smiles": self._nth_value(j, '$..data.getProductDetail.attributes[?@.key="smiles string"].values[0]'),
            "img_url": rel_img and urljoin(response.url, rel_img),
            "prd_url": response.url,
            "attrs": dumps(attrs)
        }
        yield RawData(**d)

        yield self.make_price_request(
            brand,
            catalog_id,
            prd_key,
            cat_no,
            material_ids,
            callback=self.parse_package,
            meta={"prd": d}
        )

    def parse_package(self, response):
        prd = response.meta.get("prd")
        j = json.loads(response.text)
        rows = parse('$..materialPricing[*]').find(j)
        now = datetime.now()
        for row in rows:
            available = first(parse('@.availabilities[?@key="AVAILABLE_TO_SHIP_ON"]').find(row), None)
            ts = (m := first(parse('@.availabilities[0].date').find(row), None)) and m.value
            delivery = None
            if isinstance(ts, int):
                delivery = (datetime.fromtimestamp(ts/1000) - now).days
            dd = {
                "brand": prd.get("brand"),
                "cat_no": prd.get("cat_no"),
                "package": self._nth_value(row, '@.packageSize'),
                "cost": self._nth_value(row, '@.netPrice'),
                "price": self._nth_value(row, '@.netPrice'),
                "currency": self._nth_value(row, '@.currency'),
                "stock_num": available and 1,
                "delivery_time": delivery,
            }
            yield ProductPackage(**dd)

            ddd = {
                "platform": self.name,
                "source_id": f'{prd.get("brand")}_{prd.get("cat_no")}',
                "vendor": self.name,
                "brand": prd.get("brand"),
                "cat_no": prd.get("cat_no"),
                "package": dd.get("package"),
                "discount_price": dd.get("cost"),
                "price": dd.get("price"),
                "currency": dd.get("currency"),
                "stock_num": dd.get("stock_num"),
                "delivery": dd.get("delivery_time"),
            }
            yield RawSupplierQuotation(**ddd)
