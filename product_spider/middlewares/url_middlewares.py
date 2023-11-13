from urllib.parse import unquote


class StopQuotingUrlMiddleware:
    """
    Just for simsonpharma.com
    they treat unquote url normally, but 404 for quoted url
    """
    def process_request(self, request, spider):
        request._url = unquote(request.url)
