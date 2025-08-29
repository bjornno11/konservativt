
# Register your models here.
from .models import PageView

# audit/admin.py
from django.contrib import admin
from django.utils.html import format_html

try:
    from .models import PageView
except Exception:  # skulle ikke skje, men vi vil aldri 500'e på import
    PageView = None


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    """
    Ultra-robust admin som dynamisk velger eksisterende felter.
    Unngår 500 selv om modellen endres.
    """

    # Ikke sett list_display statisk – bygg det basert på faktiske felter:
    def get_list_display(self, request):
        # alle “vanlige” DB-felter
        fields = set(f.name for f in self.model._meta.fields)

        # ønskerekkefølge – tas med hvis de finnes
        preferred = [
            "id", "created", "timestamp", "when",
            "user", "ip", "method", "path",
            "status_code", "duration_ms", "referrer", "user_agent",
        ]

        cols = [f for f in preferred if f in fields]
        if "id" not in cols and "id" in fields:
            cols.insert(0, "id")

        # Fyll på opptil 8 kolonner totalt, med hva som helst som finnes
        if len(cols) < 8:
            extra = [f for f in fields if f not in cols]
            cols += extra[: 8 - len(cols)]

        # Som siste utvei: minst én kolonne
        return tuple(cols or ("id",))

    # Safe defaults
    ordering = ("-id",)
    list_per_page = 50
    search_fields = ()      # kan aktiveres senere når vi vet feltnavn
    list_filter = ()        # dtto
    date_hierarchy = None   # aldri pek på et felt som kanskje ikke finnes

    # Hvis modellen har store tekstfelt (f.eks. user_agent), begrens visningen pent
    def _short(self, s, n=80):
        return (s[: n - 1] + "…") if isinstance(s, str) and len(s) > n else s

    # Eksempel: vis kort path / UA om de finnes (brukes kun hvis `get_list_display` tar dem med)
    def path(self, obj):
        val = getattr(obj, "path", "")
        return self._short(val, 120)

    def user_agent(self, obj):
        val = getattr(obj, "user_agent", "")
        return self._short(val, 60)
