

def rawdata_to_supplier_product(
        d: dict,
        platform: str,
        vendor: str,
):
    ret = {
        "platform": platform,
        "vendor": vendor,
        "source_id": f'{d["brand"]}_{d["cat_no"]}',
        "brand": d["brand"],
        "cat_no": d.get("cat_no"),
        "parent": d.get("parent"),
        "en_name": d.get("en_name"),
        "cas": d.get("cas"),
        "smiles": d.get("smiles"),
        "mf": d.get("mf"),
        "mw": d.get("mw"),
        "img_url": d.get("img_url"),
        "prd_url": d.get("prd_url"),
    }
    return ret


def product_package_to_raw_supplier_quotation(
        d: dict,
        dd: dict,
        platform: str,
        vendor: str,
):
    ret = {
        "platform": platform,
        "vendor": vendor,
        "brand": dd["brand"],
        "source_id": f'{dd["brand"]}_{dd["cat_no"]}',
        "cat_no": dd["cat_no"],
        "package": dd.get('package'),
        "discount_price": dd.get('cost'),
        "price": dd.get('cost'),
        "cas": d.get("cas"),
        "currency": dd["currency"],
    }
    return ret
