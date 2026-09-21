import json
from pathlib import Path

import pytest
from scrapy.http import Request, TextResponse

from product_spider.items import (
    ProductPackage,
    RawData,
    RawSupplierQuotation,
    SupplierProduct,
)
from product_spider.spiders.sunwaypharm_spider import SunwaypharmSpider

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://sunwaypharm.cn"
DETAIL_URL = f"{BASE}/product/149836.html"


def make_html_response(fixture: str, url: str, meta: dict = None) -> TextResponse:
    body = (FIXTURES / fixture).read_bytes()
    return TextResponse(url=url, body=body, encoding="utf-8", request=Request(url, meta=meta))


def test_parse_list_extracts_products_and_next_page():
    spider = SunwaypharmSpider()
    results = list(spider.parse(make_html_response("sunwaypharm_list.html", f"{BASE}/products/618/")))
    detail_requests = [r for r in results if isinstance(r, Request) and r.callback == spider.parse_detail]
    page_requests = [r for r in results if isinstance(r, Request) and r.callback == spider.parse]

    assert len(detail_requests) == 20
    assert detail_requests[0].url == DETAIL_URL
    assert detail_requests[0].meta["pd_id"] == "149836"
    assert all("sunwaypharm.cn" in r.url for r in detail_requests)
    assert len(page_requests) == 1
    assert page_requests[0].url == f"{BASE}/products/618.html?page=2&prop_filter=%7b%7d"


def test_parse_detail_extracts_fields_and_requests_loadgoods():
    spider = SunwaypharmSpider()
    results = list(
        spider.parse_detail(
            make_html_response("sunwaypharm_detail.html", DETAIL_URL, {"pd_id": "149836"})
        )
    )
    assert len(results) == 1
    req = results[0]
    assert req.method == "POST"
    assert req.url == f"{BASE}/index.aspx?a=ajaxpro_ajax&method=LoadGoods"
    assert req.body == b"pd_id=149836"
    d = req.meta["product"]
    assert d["cas"] == "1363381-10-5"
    assert "PYRAZOLO" in d["en_name"].upper()
    assert d["prd_url"] == DETAIL_URL
    assert "parent" in d and "img_url" in d and "mf" in d and "mw" in d


def _detail_meta():
    return {
        "pd_id": "149836",
        "product": {
            "chs_name": "5-溴吡唑并[1,5-a]吡啶-2-羧酸",
            "en_name": "5-Bromopyrazolo[1,5-a]pyridine-2-carboxylic acid",
            "cas": "1363381-10-5",
            "mf": None,
            "mw": None,
            "parent": "其他中间体",
            "img_url": None,
            "prd_url": DETAIL_URL,
        },
    }


def test_parse_package_yields_all_packages():
    spider = SunwaypharmSpider()
    results = list(
        spider.parse_package(
            make_html_response("sunwaypharm_loadgoods.json",
                               f"{BASE}/index.aspx?a=ajaxpro_ajax&method=LoadGoods",
                               _detail_meta())
        )
    )
    raws = [r for r in results if isinstance(r, RawData)]
    pkgs = [r for r in results if isinstance(r, ProductPackage)]
    sps = [r for r in results if isinstance(r, SupplierProduct)]
    quotes = [r for r in results if isinstance(r, RawSupplierQuotation)]

    assert len(raws) == len(pkgs) == len(sps) == len(quotes) == 4
    by_package = {p["package"]: p for p in pkgs}
    assert by_package["50mg"]["cost"] == 794.2
    assert by_package["1g"]["cost"] == 4633.15
    pkg = by_package["100mg"]
    assert pkg["brand"] == "相辉"
    assert pkg["cat_no"] == "CB40054"
    assert pkg["currency"] == "CNY"
    assert pkg["stock_num"] == 0
    assert pkg["delivery_time"] is None
    assert raws[0]["purity"] == "95+%"


def test_parse_package_bad_json_skips():
    spider = SunwaypharmSpider()
    resp = TextResponse(url=f"{BASE}/index.aspx", body=b"not json", encoding="utf-8",
                        request=Request(f"{BASE}/index.aspx", meta=_detail_meta()))
    assert list(spider.parse_package(resp)) == []


def test_keyword_search():
    spider = SunwaypharmSpider()
    requests = list(spider.keyword_search("acetone"))
    assert len(requests) == 1
    assert requests[0].url == f"{BASE}/search.do?a=is&psize=18&kw=acetone&searchtmp="
    assert requests[0].callback == spider.parse
