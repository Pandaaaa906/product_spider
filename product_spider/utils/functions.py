
def strip(string: str, default=None):
    if string is None:
        return default
    return string.strip() or None


def first(l: list, default=None):
    if not l:
        return default
    return l[0]
