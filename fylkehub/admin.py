from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import FylkeSite

@admin.register(FylkeSite)
class FylkeSiteAdmin(admin.ModelAdmin):
    list_display = ("fylke", "tittel", "offentlig")
    list_filter  = ("offentlig",)
    search_fields = ("fylke__navn", "tittel")
