
# Register your models here.
from django.contrib import admin
from .models import PageView

@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("at", "user", "ip", "method", "path")
    list_filter = ("method",)
    search_fields = ("user__username", "ip", "path", "ua")
    date_hierarchy = "at"
