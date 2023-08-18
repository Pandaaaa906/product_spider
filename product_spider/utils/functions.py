import json
from functools import partial


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


dumps = partial(json.dumps, ensure_ascii=False)
