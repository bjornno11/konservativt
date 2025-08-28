from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import DocFolder, Document

@admin.register(DocFolder)
class DocFolderAdmin(admin.ModelAdmin):
    list_display = ("navn", "opprettet_av", "opprettet")
    search_fields = ("navn", "beskrivelse")
    filter_horizontal = ("can_read", "can_write")  # NYTT

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("tittel", "folder", "opprettet_av", "opprettet")
    search_fields = ("tittel", "merknad")
    list_filter = ("folder",)
