from jsonpath_ng.ext import parse
from more_itertools import nth


def json_nth_value(d: dict, path: str, n: int = 0, default=None):
    ret = (m := nth(parse(path).find(d), n, None)) and m.value or default
    return ret


def json_all_value(d: dict, path: str):
    ret = [m.value for m in parse(path).find(d)]
    return ret
