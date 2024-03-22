import re

currency = (
    (r'[\$€£¥₹￥元,]', ''),
)


def parse_cost(cost: str):
    if not cost:
        return None
    ret = cost.strip()
    for pattern, repl in currency:
        ret = re.sub(pattern, repl, ret)
    return ret.strip()
