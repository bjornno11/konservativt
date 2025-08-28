# docs/models.py
from django.conf import settings
from django.db import models

class OrgUnit(models.Model):
    LEVELS = [
        ('central', 'Sentralt'),
        ('fylke', 'Fylke'),
        ('lokal', 'Lokallag'),
        ('gruppe', 'Gruppe/Prosjekt'),
    ]
    name = models.CharField(max_length=120)
    level = models.CharField(max_length=12, choices=LEVELS)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    class Meta:
        ordering = ['level', 'name']

    def __str__(self):
        return self.name


class RoleType(models.Model):
    """
    Rolle-typer. Navn + rekkefølge (power) så admin/red kan rangeres over bidragsyter/leser.
    """
    slug = models.SlugField(unique=True)  # 'reader', 'contributor', 'editor', 'admin'
    name = models.CharField(max_length=60)  # 'Leser', 'Bidragsyter', ...
    power = models.PositiveSmallIntegerField(default=10)  # høyere = mer makt

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Bruker har en gitt rolletype på et OrgUnit.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role_type = models.ForeignKey(RoleType, on_delete=models.CASCADE)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)
    starts_at = models.DateField(null=True, blank=True)
    ends_at = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [('user', 'role_type', 'org_unit')]

    def __str__(self):
        return f"{self.user} – {self.role_type} @ {self.org_unit}"


class Folder(models.Model):
    """
    Hvis du allerede har Folder – behold den du har.
    """
    name = models.CharField(max_length=120)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    def __str__(self):
        return self.name


class Document(models.Model):
    VISIBILITY = [
        ('public', 'Offentlig'),
        ('internal', 'Internt (innloggede)'),
        ('private', 'Privat (eier/red/adm)'),
    ]
    STATUS = [
        ('draft', 'Utkast'),
        ('pending', 'Til godkjenning'),
        ('published', 'Publisert'),
        ('archived', 'Arkivert'),
    ]

    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='docs/%Y/%m/')
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='my_documents')
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.PROTECT, help_text="Organisasjonsnivå dokumentet tilhører")
    visibility = models.CharField(max_length=10, choices=VISIBILITY, default='internal')
    status = models.CharField(max_length=10, choices=STATUS, default='draft')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title


class DocumentRoleGrant(models.Model):
    """
    Dokument-spesifikk ACL for roller.
    Eksempel: role=Leser, org_unit=(Fylke X), scope='down' -> lokallag under Fylke X får lesetilgang.
    """
    SCOPE = [
        ('same', 'Samme nivå'),
        ('down', 'Nedover (descendants)'),
        ('up', 'Oppover (ancestors)'),
    ]
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='role_grants')
    role_type = models.ForeignKey(RoleType, on_delete=models.CASCADE)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, help_text="Anker for scope")
    scope = models.CharField(max_length=8, choices=SCOPE, default='same')

    can_view = models.BooleanField(default=True)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Dokument-rolle-tilgang"
        verbose_name_plural = "Dokument-rolle-tilganger"

    def __str__(self):
        return f"{self.document} – {self.role_type} @ {self.org_unit} ({self.scope})"
