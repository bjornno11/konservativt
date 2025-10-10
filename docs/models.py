
# Create your models here.
# f.eks. people/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from members.models import Medlem, Fylkeslag, Lokallag

class Medlem(models.Model):
    fornavn   = models.CharField("Fornavn", max_length=100)
    etternavn = models.CharField("Etternavn", max_length=100)
    epost     = models.CharField("E-post", max_length=150)

    class Meta:
        verbose_name = "Medlem"
        verbose_name_plural = "Medlemmer"
        ordering = ["etternavn", "fornavn"]  # valgfritt eksempel

User = get_user_model()

# app: docs/models.py

class Dokument(models.Model):
    LAGTYPE_VALG = [
        ("sentral", "Sentralstyret"),
        ("fylke", "Fylkeslag"),
        ("lokal", "Lokallag"),
    ]

    navn = models.CharField(max_length=200)
    beskrivelse = models.TextField(blank=True)
    fil = models.FileField(upload_to="dokumenter/%Y/%m/")
    opplastet_av = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    lagtype = models.CharField(max_length=10, choices=LAGTYPE_VALG)
    lag_id = models.PositiveIntegerField()        # peker til Fylkeslag.id eller Lokallag.id
    opprettet = models.DateTimeField(auto_now_add=True)
    endret = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-opprettet"]

    def __str__(self):
        return self.navn


class Mappe(models.Model):
    navn = models.CharField(max_length=100)
    lagtype = models.CharField(max_length=10, choices=Dokument.LAGTYPE_VALG)
    lag_id = models.PositiveIntegerField()
    opprettet = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.navn


class Endring(models.Model):
    dokument = models.ForeignKey(Dokument, on_delete=models.CASCADE, related_name="endringer")
    endret_av = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    dato = models.DateTimeField(auto_now_add=True)
    beskrivelse = models.CharField(max_length=255, blank=True)
    gammel_fil = models.FileField(upload_to="dokumenter/arkiv/%Y/%m/", blank=True, null=True)

    class Meta:
        ordering = ["-dato"]

    def __str__(self):
        return f"{self.dokument.navn} endret {self.dato:%Y-%m-%d}"
