import threading

_local = threading.local()


class CurrentRequestMiddleware:
    """Expose la requête HTTP courante au thread (ex. signaux → messages)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


def get_current_request():
    return getattr(_local, "request", None)
