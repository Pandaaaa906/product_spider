import scrapyautodb as scrapy


class IchembioData(scrapy.OrderedItem):
    cas = scrapy.Field()  # CAS No.
    zh_name = scrapy.Field()  # 中文名称
    en_name = scrapy.Field()  # 英文名称
    synonyms_zh = scrapy.Field()  # 中文同义词
    synonyms_en = scrapy.Field()  # 英文同义词
    iupac_name = scrapy.Field()  # IUPAC Name
    mf = scrapy.Field()  # 分子式
    mw = scrapy.Field()  # 分子量
    smiles = scrapy.Field()  # Smiles
    inchi_key = scrapy.Field()  # InChI key
    reaxy_rn = scrapy.Field()  # Reaxy-Rn
    mdl_number = scrapy.Field()  # MDL编号
    pubchem_id = scrapy.Field()  # PubChem编号

    autoignition_temp = scrapy.Field()  # 自燃温度
    appearance = scrapy.Field()  # 形态
    refractive_index = scrapy.Field()  # 折射率
    melting_point = scrapy.Field()  # 熔点
    boiling_point = scrapy.Field()  # 沸点
    solubility = scrapy.Field()  # 溶解性
    density = scrapy.Field()  # 密度
    flash_point_f = scrapy.Field()  # 闪点(°F)
    flash_point_c = scrapy.Field()  # 闪点(°C)
    optical_rotation = scrapy.Field()  # 旋光
    sensitivity = scrapy.Field()  # 敏感性
    storage_temp = scrapy.Field()  # 储存温度
    transport_condition = scrapy.Field()  # 运输条件
    description = scrapy.Field()  # 描述及应用

    ghs_icons = scrapy.Field()  # 象形图，GHS 代码 JSON 列表
    signal_word = scrapy.Field()  # 警示用语
    hazard_statements = scrapy.Field()  # 危险声明
    precautionary_statements = scrapy.Field()  # 预防措施说明
    danger_level = scrapy.Field()  # 危险级别
    un_number = scrapy.Field()  # UN编码
    package_grade = scrapy.Field()  # 包装等级
    hazard_class = scrapy.Field()  # 危险分类
    storage_class = scrapy.Field()  # 储存分类代码
    wgk = scrapy.Field()  # WGK
    ppe = scrapy.Field()  # 个人防护装备

    url = scrapy.Field()

    class Meta:
        indexes = (
            (('cas',), True),
        )
