from django.db import models
from django.conf import settings
from geo.models import Kommune, Postnummer, Fylke
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

FYLKESLAG_ROLLER = (
    ("leder", "Leder"),
    ("styre", "Styremedlem"),
    ("medlem", "Medlem"),
)

VERVE_KILDE_CHOICES = (
    ("self", "Selvregistrering"),
    ("verver", "Vervet av"),
)

# members/models.py (tillegg)
STATUS_CHOICES = (("pending","Til godkjenning"), ("approved","Godkjent"))
status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="approved")
approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_members")
approved_at = models.DateTimeField(null=True, blank=True)


class Lokallag(models.Model):
    navn = models.CharField(max_length=150)
    kommune = models.ForeignKey(Kommune, on_delete=models.PROTECT, null=True, blank=True)
    fylke = models.ForeignKey(Fylke, on_delete=models.PROTECT)  # påkrevd
    slug = models.SlugField(max_length=140, blank=True, null=True, unique=True)

    homepage_title = models.CharField(max_length=200, blank=True)
    homepage_intro = models.TextField(blank=True)
    contact_email = models.EmailField(max_length=254, blank=True, null=True)  # NB: null=True
    contact_phone = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to="logos/lokal/", blank=True, null=True)

    class Meta:
        ordering = ["navn"]
        verbose_name = "Lokallag"
        verbose_name_plural = "Lokallag"

    def __str__(self): return f"{self.navn} ({self.fylke.navn})"

class Fylkeslag(models.Model):
    fylke       = models.OneToOneField(Fylke, on_delete=models.PROTECT, related_name="fylkeslag")
    navn        = models.CharField(max_length=128)
    epost       = models.EmailField(blank=True)
    telefon     = models.CharField(max_length=20, blank=True)
    adresse     = models.CharField(max_length=200, blank=True)
    leder_navn  = models.CharField(max_length=128, blank=True)
    opprettet   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fylke__navn"]
        verbose_name = "Fylkeslag"
        verbose_name_plural = "Fylkeslag"

    def __str__(self):
        return self.navn

    def get_absolute_url(self):
        return reverse("members:fylkeslag-detail", args=[self.pk])

    @property
    def fylkeslag(self):
        # Praktisk snarvei: fra lokallag -> tilhørende fylkeslag (via geo.Fylke)
        return getattr(self.fylke, "fylkeslag", None)



class Medlem(models.Model):
    fornavn     = models.CharField(max_length=100)
    etternavn   = models.CharField(max_length=100)
    epost       = models.EmailField(blank=True)  # valgfritt
    adresse     = models.CharField(max_length=200, blank=True)
    telefon     = models.CharField(max_length=20, db_index=True)  # PÅKREVD i form (ikke unique)
    fodselsdato = models.DateField(null=True, blank=True)

    postnummer  = models.ForeignKey(Postnummer, on_delete=models.PROTECT, null=True, blank=True)
    kommune     = models.ForeignKey(Kommune, on_delete=models.PROTECT,  null=True, blank=True)

    verve_kilde = models.CharField(max_length=10, choices=VERVE_KILDE_CHOICES, default="self")
    verver_navn = models.CharField(max_length=128, blank=True)
    verver_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medlemsprofil",
    )

    # M2M via gjennom-tabell: gir rom for felt som fra/til-dato senere
    lokallag    = models.ManyToManyField("Lokallag", through="Medlemskap", related_name="medlemmer", blank=True)

    registrert  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["etternavn", "fornavn"]
        verbose_name = "Medlem"
        verbose_name_plural = "Medlemmer"
        permissions = [
            ("approve_member", "Kan godkjenne selvregistreringer"),
        ]
    def __str__(self):
        return f"{self.etternavn}, {self.fornavn}"

    def save(self, *args, **kwargs):
        """
        Sett kommune automatisk fra postnummer (dersom primærkobling finnes).
        """
        if not self.kommune and self.postnummer:
            pk_rel = getattr(self.postnummer, "kommuner", None)  # forventer relasjon Postnummer->PostnummerKommune som 'kommuner'
            if pk_rel:
                pk = pk_rel.filter(primar=True).select_related("kommune").first()
                if pk:
                    self.kommune = pk.kommune
        super().save(*args, **kwargs)


class Medlemskap(models.Model):
    medlem    = models.ForeignKey(Medlem,   on_delete=models.CASCADE, related_name="medlemskap")
    lokallag  = models.ForeignKey(Lokallag, on_delete=models.CASCADE, related_name="medlemskap")
    startdato = models.DateField(auto_now_add=True)
    # til_dato = models.DateField(null=True, blank=True)  # legg til ved behov senere

    class Meta:
        unique_together = [("medlem", "lokallag")]
        verbose_name = "Medlemskap"
        verbose_name_plural = "Medlemskap"

    def __str__(self):
        return f"{self.medlem} → {self.lokallag}"
# members/models.py
class PendingMedlem(Medlem):
    class Meta:
        proxy = True
        verbose_name = "Selvregistrering til godkjenning"
        verbose_name_plural = "Selvregistreringer til godkjenning"
class Fylkeslagsmedlemskap(models.Model):
    medlem     = models.ForeignKey("Medlem", on_delete=models.CASCADE)
    fylkeslag  = models.ForeignKey(Fylkeslag, on_delete=models.CASCADE)
    rolle      = models.CharField(max_length=20, choices=FYLKESLAG_ROLLER, default="medlem")
    startdato  = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = (("medlem", "fylkeslag"),) 

    def __str__(self):
        return f"{self.medlem} @ {self.fylkeslag} ({self.rolle})"

    def clean(self):
        super().clean()
        if self.medlem_id and self.fylkeslag_id:
            # må ha minst ett lokallag i samme fylke
            same_fylke = self.medlem.lokallag.filter(
                fylke_id=self.fylkeslag.fylke_id
            ).exists()
            if not same_fylke:
                raise ValidationError(
                    "Medlemmet må være medlem i et lokallag i samme fylke for å kunne "
                    "registreres i fylkeslaget."
                )
# members/models.py tillegg etter sentral

class Rolle(models.Model):
    """
    Felles rollekatalog med scope for hvilket nivå rollen gjelder.
    scope: 'lokal', 'fylke', 'sentral'
    """
    SCOPE_CHOICES = (
        ("lokal", "Lokallag"),
        ("fylke", "Fylkeslag"),
        ("sentral", "Sentralstyre"),
    )
    navn = models.CharField(max_length=100)
    kode = models.SlugField(max_length=100, blank=True)  # valgfri nøkkel, f.eks. 'leder'
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    rang = models.PositiveIntegerField(default=100)      # lavere = viktigere

    class Meta:
        unique_together = [("kode", "scope")]
        ordering = ("scope", "rang", "navn")

    def __str__(self):
        return f"{self.get_scope_display()}: {self.navn}"


class SentralstyreMedlemskap(models.Model):
    """
    Medlemskap i sentralstyret med rolle og gyldighetsperiode (historikk).
    """
    medlem = models.ForeignKey("Medlem", on_delete=models.CASCADE, related_name="sentralverv")
    rolle = models.ForeignKey("Rolle", on_delete=models.PROTECT, limit_choices_to={"scope": "sentral"})
    startdato = models.DateField(default=timezone.now)
    sluttdato = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Sentralstyre-medlemskap"
        verbose_name_plural = "Sentralstyre-medlemskap"
        ordering = ("-startdato",)

    @property
    def aktiv(self):
        return self.sluttdato is None or self.sluttdato >= timezone.now().date()

    def __str__(self):
        til = f"– {self.sluttdato}" if self.sluttdato else "–"
        return f"{self.medlem} • {self.rolle.navn} ({self.startdato} {til})"
