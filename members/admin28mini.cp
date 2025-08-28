# members/admin.py — SAFE MODE
from django.contrib import admin
from .models import Medlem, Lokallag

@admin.register(Lokallag)
class LokallagAdmin(admin.ModelAdmin):
    list_display = ("id", "navn", "fylke")
    search_fields = ("navn",)
    ordering = ("navn",)

@admin.register(Medlem)
class MedlemAdmin(admin.ModelAdmin):
    list_display = ("id", "visning")  # bare id + __str__
    search_fields = ()                # tomt enn så lenge
    ordering = ("id",)

    def visning(self, obj):
        return str(obj)
    visning.short_description = "Navn"
