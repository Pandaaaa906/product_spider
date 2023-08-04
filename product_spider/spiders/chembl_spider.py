import json
from base64 import b64encode

from scrapy import Request

from product_spider.items import ChemblMolecule
from product_spider.utils.spider_mixin import BaseSpider


class CheEMBLSpider(BaseSpider):
    name = "chembl"
    url_api = "https://www.ebi.ac.uk/chembl/interface_api/es_proxy/es_data/get_es_data"
    url_detail = "https://www.ebi.ac.uk/chembl/interface_api/es_proxy/es_data/get_es_document/chembl_molecule"

    custom_settings = {
        "URLLENGTH_LIMIT": 90000
    }

    def start_requests(self):
        es_query = {
            "_source": ["molecule_chembl_id", "pref_name", "molecule_synonyms", "molecule_type", "max_phase",
                        "molecule_properties.full_mwt", "_metadata.related_targets.count",
                        "_metadata.related_activities.count", "molecule_properties.alogp", "molecule_properties.psa",
                        "molecule_properties.hba", "molecule_properties.hbd", "molecule_properties.num_ro5_violations",
                        "molecule_properties.rtb", "molecule_properties.ro3_pass", "molecule_properties.qed_weighted",
                        "molecule_properties.cx_most_apka", "molecule_properties.cx_most_bpka",
                        "molecule_properties.cx_logp", "molecule_properties.cx_logd",
                        "molecule_properties.aromatic_rings", "structure_type", "inorganic_flag",
                        "molecule_properties.heavy_atoms", "molecule_properties.hba_lipinski",
                        "molecule_properties.hbd_lipinski", "molecule_properties.num_lipinski_ro5_violations",
                        "molecule_properties.mw_monoisotopic", "molecule_properties.np_likeness_score",
                        "molecule_properties.molecular_species", "molecule_properties.full_molformula",
                        "molecule_structures.canonical_smiles", "molecule_structures.standard_inchi_key",
                        "polymer_flag"], "query": {
                "bool": {"must": {"bool": {"boost": 1, "must": {"bool": {"must": [], "should": []}}}},
                         "filter": [[
                             {"bool": {"should": [{"term": {"molecule_type": "Small molecule"}}]}},
                             {"bool": {"should": [
                                 {"term": {"_metadata.compound_generated.max_phase_label": "Phase 3"}},
                                 {"term": {"_metadata.compound_generated.max_phase_label": "Approved"}}
                             ]}},
                         ]]}},
            "track_total_hits": True, "sort": []}
        yield self.make_request(
            'chembl_molecule', es_query,
            limit=24, offset=0,
            callback=self.parse
        )

    def make_request(
            self, index_name: str, es_query: dict,
            limit: int = 24, offset: int = 0, contextual_sort_data: dict = None,
            meta: dict = None, **kwargs
    ):
        if meta is None:
            meta = {}
        es_query = es_query.copy()
        es_query["size"] = limit
        es_query["from"] = offset
        return self._make_request(
            index_name, es_query, contextual_sort_data,
            meta={"limit": limit, "offset": offset, "es_query": es_query, "index_name": "chembl_molecule", **meta},
            **kwargs)

    def _make_request(
            self, index_name: str, es_query: dict, contextual_sort_data: dict = None,
            **kwargs
    ):
        if contextual_sort_data is None:
            contextual_sort_data = {}
        params = {
            "index_name": index_name,
            "es_query": json.dumps(es_query),
            "contextual_sort_data": json.dumps(contextual_sort_data)
        }
        t = b64encode(json.dumps(params).encode()).decode()
        return Request(
            url=f"{self.url_api}/{t}",
            **kwargs
        )

    def parse(self, response, **kwargs):
        j = json.loads(response.text)
        index_name = response.meta.get('index_name', None)
        limit = response.meta.get('limit', 24)
        offset = response.meta.get('offset', 0)
        es_query = response.meta.get('es_query', {})

        records = j.get('es_response', {}).get('hits', {}).get('hits', [])
        if not isinstance(records, list):
            return
        for record in records:
            chembl_id = record['_id']
            yield Request(
                url=f"{self.url_detail}/{chembl_id}",
                callback=self.parse_detail
            )
            pass
        pass
        if not records:
            return
        if not all((index_name, es_query)):
            return
        yield self.make_request(
            index_name,
            es_query,
            limit=limit,
            offset=offset + limit,
            callback=self.parse
        )

    def parse_detail(self, response):
        j = json.loads(response.text)
        chembl_id = j.get("_id")
        raw_json = j.get("_source")
        if not all((chembl_id, raw_json)):
            return
        d = {
            "chembl_id": chembl_id,
            "raw_json": json.dumps(raw_json)
        }
        yield ChemblMolecule(**d)
        pass
