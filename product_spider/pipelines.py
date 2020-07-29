# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DropNullCatNoPipeline:

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # Skip items dont have key `cat_no`
        if 'cat_no' not in adapter:
            return item
        cat_no = adapter.get('cat_no')
        if cat_no is None or not cat_no.strip():
            raise DropItem("Missing cat_no in %s" % item)
        adapter['cat_no'] = str.strip(adapter['cat_no'])
        return item
