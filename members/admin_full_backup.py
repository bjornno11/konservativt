# members/admin.py — SAFE MODE (midlertidig)
from django.contrib import admin
from .models import Medlem, Lokallag  # legg til flere modeller senere når alt er stabilt

@admin.register(Lokallag)
class LokallagAdmin(admin.ModelAdmin):
    list_display = ("id", "navn", "fylke")   # KUN trygge felter
    search_fields = ("navn",)
    ordering = ("navn",)

@admin.register(Medlem)
class MedlemAdmin(admin.ModelAdmin):
    list_display = ("id", "visning")         # Unngår alle usikre felter
    search_fields = ()                       # Skru på senere: ("fornavn", "etternavn", "epost")
    ordering = ("id",)

    def visning(self, obj):
        return str(obj)
    visning.short_description = "Navn"
