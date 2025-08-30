# Create your models here.
from django.db import models
from django.utils.translation import gettext_lazy as _
from geo.models import Fylke

class FylkeSite(models.Model):
    """
    'Site settings' for hvert fylke sin minisite.
    Holder innhold/branding uten å røre geo.Fylke-tabellen.
    """
    fylke = models.OneToOneField(Fylke, on_delete=models.CASCADE, related_name="site")
    tittel = models.CharField(max_length=200, blank=True)
    intro  = models.TextField(blank=True)
    hero_bilde = models.ImageField(upload_to="logos/fylkehero/", blank=True, null=True)
    offentlig = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fylke-site"
        verbose_name_plural = "Fylke-sites"

    def __str__(self):
        return f"FylkeSite: {self.fylke.navn}"
