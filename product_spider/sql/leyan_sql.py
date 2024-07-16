sql_trc_cat_nos = """
select cat_no
from rawdata prd
where brand='trc'
and modify_date > %s
AND NOT EXISTS (
    SELECT 1 FROM "public"."rawsupplierquotation" t
    where t.platform='leyan' and t.brand='trc' and t.cat_no = prd.cat_no and t.modify_date >= %s
)
order by modify_date desc
"""