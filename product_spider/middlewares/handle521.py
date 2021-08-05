import json
import re
from hashlib import sha1, sha256, md5
from itertools import permutations

import execjs

hash_d = {
    'sha1': sha1,
    'sha256': sha256,
    'md5': md5,
}


def encrypt_cookies(chars, bts, ct, hash_func):
    for i in permutations(chars, 2):
        cookie = f'{bts[0]}{"".join(i)}{bts[1]}'
        if hash_func(cookie.encode()).hexdigest() == ct:
            return cookie


def get_params(response):
    return json.loads(re.findall(r';go\((.*?)\)', response.text)[0])


class Cookie521Middleware:
    cookies = {}

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        return s

    def process_request(self, request, spider):
        request.cookies.update(self.cookies)
        request.priority = 99999

    def process_response(self, request, response, spider):
        if response.status != 521:
            return response
        self.cookies = {}
        if 'document.cookie' in response.text:
            js_clearance = re.findall('cookie=(.*?);location', response.text)[0]
            result = execjs.eval(js_clearance).split(';')[0]
            k, v, *_ = result.split('=')
            self.cookies.update({k: v})
            request.dont_filter = True
            return self.process_request(request, spider) or request
        else:
            params = get_params(response)
            chars = params['chars']
            bts = params['bts']
            ha = params['ha']
            ct = params['ct']
            hash_func = hash_d[ha]
            clearance = encrypt_cookies(chars, bts, ct, hash_func)
            self.cookies['__jsl_clearance_s'] = clearance
            request.dont_filter = True
            return self.process_request(request, spider) or request
