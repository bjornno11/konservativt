from django.db import models

# Create your models here.
from django.db import models

class Fylke(models.Model):
    navn = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, blank=True, null=True, unique=True)
    homepage_title = models.CharField(max_length=200, blank=True)
    homepage_intro = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to="logos/fylke/", blank=True, null=True)

    class Meta:
        ordering = ["navn"]          # ⟵ viktig endring
        verbose_name_plural = "Fylker"

    def __str__(self):
        return self.navn

class Kommune(models.Model):
    nummer = models.CharField(max_length=4, unique=True, db_index=True)  # f.eks. "0301"
    navn   = models.CharField(max_length=128)
    fylke  = models.ForeignKey(Fylke, on_delete=models.PROTECT, related_name="kommuner")
    gyldig_fra = models.DateField(null=True, blank=True)
    gyldig_til = models.DateField(null=True, blank=True)
    aktiv = models.BooleanField(default=True)

    class Meta:
        ordering = ["nummer"]

    def __str__(self):
        return f"{self.nummer} {self.navn}"

POSTNUMMER_KATEGORIER = (
    ("G", "Gate/postboks"),
    ("B", "Postboksanlegg"),
    ("S", "Serviceboks"),
    ("F", "Felles"),  # mm. – varierer litt i Postens data
)

class Postnummer(models.Model):
    nummer   = models.CharField(max_length=4, unique=True, db_index=True)
    poststed = models.CharField(max_length=64)
    kategori = models.CharField(max_length=1, choices=POSTNUMMER_KATEGORIER, blank=True)

    class Meta:
        ordering = ["nummer"]

    def __str__(self):
        return f"{self.nummer} {self.poststed}"

class PostnummerKommune(models.Model):
    """Et postnummer kan ligge i flere kommuner (Postens datasett viser alle)."""
    postnummer = models.ForeignKey(Postnummer, on_delete=models.CASCADE, related_name="kommuner")
    kommune    = models.ForeignKey(Kommune, on_delete=models.PROTECT, related_name="postnumre")
    primar     = models.BooleanField(default=False)

    class Meta:
        unique_together = [("postnummer", "kommune")]
