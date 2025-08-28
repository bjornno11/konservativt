from django.db import models

# Create your models here.
# f.eks. people/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Medlem(models.Model):
    fornavn   = models.CharField("Fornavn", max_length=100)
    etternavn = models.CharField("Etternavn", max_length=100)
    epost     = models.CharField("E-post", max_length=150)

    class Meta:
        verbose_name = "Medlem"
        verbose_name_plural = "Medlemmer"
        ordering = ["etternavn", "fornavn"]  # valgfritt eksempel

User = get_user_model()

class DocFolder(models.Model):
    navn = models.CharField(max_length=200)
    beskrivelse = models.TextField(blank=True)
    opprettet_av = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    opprettet = models.DateTimeField(auto_now_add=True)

    # NYTT: ACL per mappe
    can_read = models.ManyToManyField(Group, blank=True, related_name="docfolders_can_read", verbose_name="Kan lese (grupper)")
    can_write = models.ManyToManyField(Group, blank=True, related_name="docfolders_can_write", verbose_name="Kan laste opp (grupper)")

    class Meta:
        verbose_name = "Mappe"
        verbose_name_plural = "Mapper"
        ordering = ["navn"]

    def __str__(self):
        return self.navn

class Document(models.Model):
    folder = models.ForeignKey(DocFolder, on_delete=models.CASCADE, related_name="docs")
    tittel = models.CharField(max_length=255)
    fil = models.FileField(upload_to="docs/%Y/%m/")
    merknad = models.TextField(blank=True)
    opprettet_av = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    opprettet = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumenter"
        ordering = ["-opprettet"]

    def __str__(self):
        return self.tittel
