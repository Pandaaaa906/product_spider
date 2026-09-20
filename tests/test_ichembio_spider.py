import json
from pathlib import Path

from scrapy.http import Request, TextResponse

from product_spider.spiders.ichembio_spider import IchembioSpider

FIXTURE = Path(__file__).parent / 'fixtures' / 'ichembio_detail_67-56-1.html'
DETAIL_URL = 'https://www.ichembio.com/cas/67-56-1'


def make_response(body: bytes, url: str = DETAIL_URL) -> TextResponse:
    return TextResponse(url=url, body=body, encoding='utf-8', request=Request(url))


def test_parse_detail_extracts_fields():
    spider = IchembioSpider()
    items = list(spider.parse_detail(make_response(FIXTURE.read_bytes())))
    assert len(items) == 1
    item = items[0]
    assert item['cas'] == '67-56-1'
    assert item['zh_name'] == '甲醇 溶液'
    assert item['en_name'] == 'Methanol'
    assert item['smiles'] == 'CO'
    assert item['mf'] == 'CH4O'  # 页面为 CH<SUB>4</SUB>O，join 后无空格
    assert item['mw'] == '32.04'
    assert item['mdl_number'] == 'MFCD00004595'
    assert item['appearance'] == 'liquid'
    assert item['un_number'] == 'UN1230'
    assert item['package_grade'] == 'II'
    assert item['danger_level'] == 'Danger'
    assert item['hazard_statements'] == 'H225,H301,H311,H331,H370'
    assert item['precautionary_statements'] == 'P210 - P260 - P280 - P301 + P310 - P311'
    assert item['wgk'] == 'WGK 1'
    assert json.loads(item['ghs_icons']) == ['GHS02', 'GHS06', 'GHS08']
    assert item['url'] == DETAIL_URL


def test_parse_detail_dash_to_none():
    spider = IchembioSpider()
    (item,) = list(spider.parse_detail(make_response(FIXTURE.read_bytes())))
    assert item['inchi_key'] is None  # 页面显示 '-'
    assert item['signal_word'] is None
    assert item['reaxy_rn'] is None


def test_parse_detail_not_found_page():
    body = '<html><head><title>页面不存在｜iChemBio</title></head><body></body></html>'
    resp = make_response(body.encode('utf-8'), url='https://www.ichembio.com/cas/000-00-0')
    spider = IchembioSpider()
    assert list(spider.parse_detail(resp)) == []
