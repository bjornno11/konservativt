# access/models.py
from django.conf import settings
from django.db import models

class OrgLevel(models.IntegerChoices):
    SENTRAL = 3, "Sentral"
    FYLKE   = 2, "Fylke"
    LOKAL   = 1, "Lokal"

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    level = models.IntegerField(choices=OrgLevel.choices)
    # eksempel: "Styreleder", "Kasserer", "Redaktør"
    def __str__(self): return f"{self.name} ({self.get_level_display()})"

class RoleAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    level = models.IntegerField(choices=OrgLevel.choices)
    org_id = models.PositiveIntegerField(null=True, blank=True)
    # org_id = None for sentralt (kan være 0/None); for fylke => fylke.id; lokal => lokallag.id

    class Meta:
        unique_together = ("user", "role", "level", "org_id")

    def __str__(self):
        return f"{self.user} → {self.role} [{self.get_level_display()}:{self.org_id or '-'}]"
