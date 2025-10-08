from .models import PageView

EXCLUDE_PREFIXES = ("/static/", "/konservativt/media/")

class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resp = self.get_response(request)
        p = request.path
        if p.startswith("/konservativt/") and not any(p.startswith(x) for x in EXCLUDE_PREFIXES):
            try:
                ip = (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()
                ua = request.META.get("HTTP_USER_AGENT", "")
                PageView.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    path=p,
                    method=request.method,
                    ip=ip or None,
                    ua=ua[:4000],
                )
            except Exception:
                pass
        return resp
