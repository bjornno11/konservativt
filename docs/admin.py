from django.contrib import admin
from .models import Mappe, Dokument, Endring


@admin.register(Mappe)
class MappeAdmin(admin.ModelAdmin):
    list_display = ("navn", "lagtype", "lag_id", "opprettet")
    list_filter = ("lagtype",)
    search_fields = ("navn",)
    ordering = ("lagtype", "navn")


@admin.register(Dokument)
class DokumentAdmin(admin.ModelAdmin):
    list_display = ("navn", "lagtype", "lag_id", "opplastet_av", "opprettet", "endret")
    list_filter = ("lagtype", "opplastet_av")
    search_fields = ("navn", "beskrivelse")
    date_hierarchy = "opprettet"
    ordering = ("-opprettet",)


@admin.register(Endring)
class EndringAdmin(admin.ModelAdmin):
    list_display = ("dokument", "endret_av", "dato", "beskrivelse")
    list_filter = ("endret_av", "dato")
    search_fields = ("dokument__navn", "beskrivelse")
    date_hierarchy = "dato"
    ordering = ("-dato",)
