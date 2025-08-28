# konservativt/middleware.py
class PrefixMiddleware:
    """
    Normaliserer SCRIPT_NAME/PATH_INFO når appen ligger under et URL-prefiks
    bak en reverse proxy (Nginx).
    Leser enten X-Forwarded-Prefix eller X-Script-Name.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        script_name = request.META.get("HTTP_X_FORWARDED_PREFIX") or request.META.get("HTTP_X_SCRIPT_NAME")
        if script_name:
            # sett SCRIPT_NAME for Django/reversering
            request.META["SCRIPT_NAME"] = script_name.rstrip("/")
            # fjern prefiks fra PATH_INFO for matching av URLconf
            path_info = request.META.get("PATH_INFO", "")
            if path_info.startswith(script_name):
                request.META["PATH_INFO"] = path_info[len(script_name):] or "/"
        return self.get_response(request)
