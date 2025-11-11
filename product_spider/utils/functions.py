import json
from functools import partial
import urllib.parse


def strip(string: str, default=None):
    if string is None:
        return default
    if not isinstance(string, str):
        return string
    return string.strip() or default


def first(l: list, default=None):
    if not l:
        return default
    return l[0]


is_not_none = lambda x: x is not None


def clean_dict(d: dict, func=is_not_none):
    return {k: v for k, v in d.items() if func(v)}


dumps = partial(json.dumps, ensure_ascii=False)


def get_url(base_url: str, target_url: str):
    if not isinstance(target_url, str) or 'javascript:' in target_url.lower():
        return None
    if not target_url.startswith('http'):
        if not isinstance(base_url, str) or not base_url.startswith('http'):
            return None
        return urllib.parse.urljoin(base_url, target_url)
    return target_url


def generate_all_cas_numbers():
    def calculate_check_digit(_cas_body: str) -> str:
        """计算CAS号的校验码"""
        digits = _cas_body.replace('-', '')
        total = sum(int(digit) * (i + 1) for i, digit in enumerate(reversed(digits)))
        return str(total % 10)

    """遍历所有合法 CAS 号"""
    for a_length in range(1, 8):
        start = 10 ** (a_length - 1)
        end = 10 ** a_length
        for a in range(start, end):
            a_str = str(a)
            for b in range(0, 100):
                b_str = f"{b:02d}"
                cas_body = a_str + b_str
                check_digit = calculate_check_digit(cas_body)
                yield f"{a_str}-{b_str}-{check_digit}"


def is_valid_element(symbol: str) -> bool:
    """
    判断传入字符串是否是合法的单质
    """
    valid_elements = {
        "B", "C", "F", "H", "I", "K", "N",
        "P", "S", "U", "V", "W", "Y", "Ag", "Al", "Fe", "Cu", "Au", "Pb", "Zn", "Sn", "Mg", "Ca", "Na", "Li", "Mn",
        "Cr", "Co", "Ni", "Pt", "Pd", 'Bi', 'Sc', 'Rh', 'Ta', 'Gd', 'Zr'
    }
    return symbol in valid_elements


def extract_adjacent_property(response, keyword: str, base_xpath: str = None, sub_text: bool = False) -> str:
    """
    常用于提取类似 <td>CAS号:</td><td>145-875-6</td> 这样的结构
    :param response: Scrapy的响应
    :param keyword: 属性名关键词 如CAS号
    :param base_xpath: 基础的xpath 用于精确匹配
    :return: str 属性值字符串
    """
    base_xpath = base_xpath or '//*'
    if sub_text:
        temp = response.xpath(f"{base_xpath}[contains(text(),'{keyword}')]/following-sibling::*[1]//text()").getall()
        temp = ''.join(temp)
        return temp
    else:
        temp = response.xpath(f"{base_xpath}[contains(text(),'{keyword}')]/following-sibling::*[1]/text()").get()
    return temp
