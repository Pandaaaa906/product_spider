from jsonpath_ng.ext import parse
from more_itertools import nth


def json_nth_value(d: dict, path: str, n=0):
    ret = (m := nth(parse(path).find(d), n, None)) and m.value
    return ret


def json_all_value(d: dict, path: str):
    ret = [m.value for m in parse(path).find(d)]
    return ret
