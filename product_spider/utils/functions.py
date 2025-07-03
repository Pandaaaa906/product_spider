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
