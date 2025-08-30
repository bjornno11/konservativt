from django.contrib import admin
from .models import Fylke, Kommune, Postnummer
# Ta med PostnummerKommune hvis du har den i models.py
try:
    from .models import PostnummerKommune
except Exception:
    PostnummerKommune = None


@admin.register(Fylke)
class FylkeAdmin(admin.ModelAdmin):
    list_display = ("navn", "slug", "homepage_public")
    list_filter  = ("homepage_public",)
    search_fields = ("navn", "slug")
    fields = ("navn", "slug", "homepage_title", "homepage_intro", "homepage_public")
    prepopulated_fields = {"slug": ("navn",)}

@admin.register(Kommune)
class KommuneAdmin(admin.ModelAdmin):
    list_display = ("nummer", "navn", "fylke", "aktiv")
    list_filter = ("fylke", "aktiv")
    search_fields = ("nummer", "navn")

@admin.register(Postnummer)
class PostnummerAdmin(admin.ModelAdmin):
    list_display = ("nummer", "poststed")
    search_fields = ("nummer", "poststed")

if PostnummerKommune:
    @admin.register(PostnummerKommune)
    class PKAdmin(admin.ModelAdmin):
        list_display = ("postnummer", "kommune", "primar")
        list_filter = ("primar", "kommune__fylke")
