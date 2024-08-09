from functools import lru_cache

from jsonpath_ng.ext import parse
from more_itertools import nth


parse = lru_cache()(parse)


def jsonpath_query_all(d: dict, path: str):
    ret = [m.value for m in parse(path).find(d)]
    return ret


def jsonpath_query_nth(d: dict, path: str, n: int = 0, default=None):
    ret = (m := nth(parse(path).find(d), n, None)) and m.value or default
    return ret
