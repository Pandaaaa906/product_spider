

sql_fetch_cas = """
SELECT
distinct cas
FROM chemhostv2.mod_product_product prd
WHERE prd.brand_name = 'cato'
AND prd.cas not ilike all(array['n/a', 'na'])
AND NOT EXISTS (SELECT 1 FROM "public"."chemsrcchemical" t where t.cas = prd.cas and t.modify_date <= %s)

ORDER BY prd.cas

"""