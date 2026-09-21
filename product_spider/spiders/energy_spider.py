import base64
import html
import json
import re

from scrapy import Request, FormRequest

from product_spider.items import (
    RawData,
    SupplierProduct,
    RawSupplierQuotation,
    ProductPackage,
)
from product_spider.utils.items_translate import (
    rawdata_to_supplier_product,
    product_package_to_raw_supplier_quotation,
)
from product_spider.utils.spider_mixin import BaseSpider


class EnergySpiderSpider(BaseSpider):
    name = "energychemical"
    brand = "energychemical"
    start_urls = [
        "https://www.energy-chemical.com/front/index.htm",
    ]
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        # 雷池 WAF：移动端 UA + requests(urllib3) TLS 指纹放行；Twisted/curl 一律 403
        # 单 IP 高频会被软封（468 维护页），低速 + 少重试
        "DOWNLOAD_HANDLERS": {
            "http": "product_spider.utils.requests_handler.RequestsDownloadHandler",
            "https": "product_spider.utils.requests_handler.RequestsDownloadHandler",
        },
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 1,
        "RETRY_ENABLED": True,
        "RETRY_HTTP_CODES": [403, 468],
        "RETRY_TIMES": 3,
        "RETRY_BACKOFF_BASE": 5,
        "RETRY_BACKOFF_MAX": 120,
    }
    num_map = {
        "β": "0",
        "⁄": "1",
        "⁜": "2",
        ":": "3",
        "−": "4",
        "ρ": "5",
        "😕": "6",
        "τ": "7",
        "😀": "8",
        "?": "9",
        "😅": ".",
    }

    def parse(self, response, **kwargs):
        seen = set()
        for el in response.xpath("//*[contains(@onclick,'getChildrenOrDetail')]"):
            match = re.search(r"'(\d+)'", el.xpath("./@onclick").get() or "")
            if not match or match.group(1) in seen:
                continue
            seen.add(match.group(1))
            parent = el.xpath("./@title").get() or el.xpath("normalize-space(.)").get()
            yield FormRequest(
                "https://www.energy-chemical.com/front/have_children.htm",
                formdata={"id": match.group(1)},
                method="POST",
                callback=self.walk_categories,
                meta={"parent": parent},
            )

    def walk_categories(self, response):
        parent = response.meta.get("parent")
        try:
            j = json.loads(response.text)
            if isinstance(j, str):  # 响应可能是双重编码的 JSON 字符串
                j = json.loads(j)
            nodes = j.get("list", [])
        except Exception as e:
            self.logger.warning(
                f"Parse category tree error, url:{response.url} err:{e}"
            )
            return
        if not nodes:
            return
        node = nodes[0]  # 实测 list[0] 即被查询节点本身
        children = node.get("children")
        if not children:
            if node.get("id") is None:
                return
            # 叶子节点 → 产品列表页
            node_id = str(node.get("id"))
            yield Request(
                f"https://www.energy-chemical.com/front/search_goodsbyclass.htm?labelId={node_id}",
                callback=self.parse_list,
                meta={"parent": parent, "label_id": node_id},
            )
            return
        for child in children:
            crumb = f"{parent}>{child.get('text')}" if parent else child.get("text")
            yield FormRequest(
                "https://www.energy-chemical.com/front/have_children.htm",
                formdata={"id": str(child.get("id"))},
                method="POST",
                callback=self.walk_categories,
                meta={"parent": crumb},
            )

    def parse_list(self, response):
        parent = response.meta.get("parent")
        label_id = response.meta.get("label_id")
        script_text = response.xpath(
            '//script[contains(text(),"tempList")]/text()'
        ).get()
        j_text = re.search(
            r"let tempList = JSON.parse\(JSON.stringify\((.+?)\)\);\s", script_text
        )
        if j_text is None:
            self.logger.warning(f"No product list json found, url:{response.url}")
            return
        j_text = j_text.group(1)
        j_text = j_text.replace(
            "\\'", "'"
        )  # JS 字符串转义 \' 不是合法 JSON，先还原（站点内嵌的是 JS 对象字面量）
        try:
            j_obj: dict = json.loads(j_text)
        except Exception as e:
            self.logger.warning(
                f"Parse product list json error, url:{response.url} err:{e}"
            )
            return
        list_token = re.search(r"let listToken = '(.+?)';", script_text)
        if list_token is None:
            self.logger.warning(f"No product list token found, url:{response.url}")
            return
        list_token = list_token.group(1)
        if not j_obj:
            return
        j_obj = j_obj[0]
        product_list = j_obj.get("list2", [])
        for item in product_list:
            item["parent"] = parent
            item["prd_url"] = response.url
            searchString = {
                "cas": item["cas"],
                "keywords": "",
                "brandBm": {},
                "spec": {},
                "classMap": {},
                "bpbSourcenm": "",
                "deliveryDate": "",
                "labelId": label_id,
                "pattern": "大图模式",
            }
            form = {
                "searchString": json.dumps(searchString),
                "currentPage": "1",
                "groupValue": j_obj.get("groupValue"),
                "listToken": list_token,
            }
            yield FormRequest(
                "https://www.energy-chemical.com/front/searchProductList.htm",
                callback=self.parse_detail,
                method="POST",
                meta={"parent": parent, "item": item},
                formdata=form,
            )
        csrf = None
        for h in response.headers.getlist("Set-Cookie"):
            m = re.search(rb"csrfToken=([^;]+)", h)
            if m:
                csrf = m.group(1).decode()
                break
        if not csrf:
            self.logger.warning(f"No csrfToken cookie found, url:{response.url}")
            return
        yield self._page_request(parent, label_id, csrf, 2)

    def _page_request(self, parent, label_id, csrf, page, prev_sign=None):
        search_map = {
            "cas": "",
            "keywords": "",
            "brandBm": {},
            "spec": {},
            "classMap": {},
            "bpbSourcenm": "",
            "deliveryDate": "",
            "labelId": label_id,
            "pattern": "大图模式",
            "elementId": "",
            "smiles": "",
            "searchStruType": "",
            "similarValue": "",
            "plcas": "",
            "ComboFlag": "",
        }
        post_obj = base64.b64encode(
            json.dumps(
                {
                    "searchString": json.dumps(search_map, ensure_ascii=False),
                    "totalPage": "",
                    "currentPage": str(page),
                    "groupValue": "试剂产品",  # 与旧爬虫行为一致，只取第一个 group
                },
                ensure_ascii=False,
            ).encode("utf-8")
        ).decode()
        return FormRequest(
            "https://www.energy-chemical.com/front/searchByQueryCriteria.htm",
            formdata={"post_obj": post_obj, "csrfToken": csrf},
            method="POST",
            callback=self.parse_page,
            meta={
                "parent": parent,
                "label_id": label_id,
                "csrf": csrf,
                "page": page,
                "prev_sign": prev_sign,
            },
        )

    def parse_page(self, response):
        parent = response.meta.get("parent")
        label_id = response.meta.get("label_id")
        csrf = response.meta.get("csrf")
        page = response.meta.get("page")
        try:
            j_obj = json.loads(response.text)
        except Exception as e:
            self.logger.warning(f"Parse page json error, url:{response.url} err:{e}")
            return
        result_list = j_obj.get("resultList") or []
        product_list = result_list[0].get("list2", []) if result_list else []
        if not product_list:
            return
        sign = (product_list[0].get("cas"), len(product_list))
        if sign == response.meta.get("prev_sign"):
            self.logger.warning(
                f"Duplicate page detected, stop pagination, url:{response.url} page:{page}"
            )
            return
        list_token = j_obj.get("listToken")
        if not list_token:
            self.logger.warning(
                f"No listToken in page response, url:{response.url} page:{page}"
            )
            return
        for item in product_list:
            cas = item.get("cas")
            if not cas:
                continue
            item["parent"] = parent
            item["prd_url"] = (
                f"https://www.energy-chemical.com/front/search_goodsbyclass.htm?labelId={label_id}"
            )
            searchString = {
                "cas": cas,
                "keywords": "",
                "brandBm": {},
                "spec": {},
                "classMap": {},
                "bpbSourcenm": "",
                "deliveryDate": "",
                "labelId": label_id,
                "pattern": "大图模式",
            }
            form = {
                "searchString": json.dumps(searchString, ensure_ascii=False),
                "currentPage": str(page),
                "groupValue": "试剂产品",
                "listToken": list_token,
            }
            yield FormRequest(
                "https://www.energy-chemical.com/front/searchProductList.htm",
                callback=self.parse_detail,
                method="POST",
                meta={"parent": parent, "item": item},
                formdata=form,
            )
        yield self._page_request(parent, label_id, csrf, page + 1, prev_sign=sign)

    def parse_stock_num(self, qty_map: dict):
        try:
            if type(qty_map) is not dict:
                return None
            total_qty = sum([float(x[0]) for x in qty_map.values()])
            return total_qty
        except Exception:
            self.logger.warning(f"Parse stock number error, qty_map:{qty_map}")
            return None

    def parse_price(self, price_str: str):
        decoded = html.unescape(price_str)
        trans_table = str.maketrans(self.num_map)
        return decoded.translate(trans_table)

    def parse_detail(self, response):
        try:
            product_obj: dict = json.loads(f"[{response.text}]")
        except Exception as e:
            self.logger.error(
                f"Parse product detail json error, url:{response.url} err:{e}"
            )
            return
        if not product_obj[0].get("tokenFlag", True):
            self.logger.warning(
                f"Invalid listToken (tokenFlag false), url:{response.url}"
            )
            return
        products = product_obj[0].get("resultList")
        if not products:
            return
        item = response.meta.get("item", {})
        cas = products[0].get("list2", [])[0].get("cas")
        products = products[0].get("list2", [])[0].get("mstList", [])
        for p in products:
            d = {
                "brand": self.brand,
                "parent": response.meta.get("parent"),
                "cat_no": p.get("bpmOrgcd"),
                "en_name": item.get("bpsEnm"),
                "chs_name": p.get("bpmNm"),
                "cas": cas,
                "mf": item.get("bpsMf"),
                "mw": item.get("bpsMw"),
                "prd_url": item.get("prd_url"),
                "img_url": item.get("casImg"),
                "mdl": item.get("bpsMDL"),
                "info2": p.get("storageDesc"),
                "purity": p.get("bpacPurity"),
            }
            yield RawData(**d)
            ddd = rawdata_to_supplier_product(d, platform=self.name, vendor=self.name)
            pkg_list = p.get("pkgList", [])
            yield SupplierProduct(**ddd)
            for pkg in pkg_list:
                price = self.parse_price(pkg.get("price"))
                stock_num = self.parse_stock_num(pkg.get("qtyMap"))
                if isinstance(stock_num, float):
                    stock_num = int(stock_num)
                dd = {
                    "brand": self.name,
                    "cat_no": d["cat_no"],
                    "package": pkg.get("specMap", {}).get("规格"),
                    "cost": price,
                    "price": price,
                    "currency": "CNY",
                    "delivery_time": pkg.get("specMap", {}).get("货期"),
                    "purity": d["purity"],
                    "stock_num": stock_num,
                }
                yield ProductPackage(**dd)
                if dd["cost"]:
                    yield RawSupplierQuotation(
                        **product_package_to_raw_supplier_quotation(
                            d, dd, platform=self.name, vendor=self.name
                        )
                    )
