

sql_fetch_cas = """
SELECT
cas
FROM chemhostv2.mod_product_product prd
WHERE prd.brand_name = 'cato'
AND prd.cas ~ '\d+-\d+-\d'
AND NOT EXISTS (SELECT 1 FROM "public"."chemsrcchemical" t where t.cas = prd.cas and t.modify_date >= %s)
GROUP BY prd.cas
ORDER BY length(prd.cas), prd.cas

"""