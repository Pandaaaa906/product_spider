import re

units = (
    ('/ ?[支瓶]$', ''),
    ('^约?', ''),
    ('(?<=\d) ', ''),

    (' ?毫克$', 'mg'),
    (' ?毫升$', 'mL'),
    (' ?克$', 'g'),
    (' ?升$', 'L'),
)


def parse_package(package: str):
    """用于处理规格信息"""
    ret = package
    for pattern, repl in units:
        ret = re.sub(pattern, repl, ret)
    return ret.strip()
