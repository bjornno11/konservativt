
# Create your models here.
from django.db import models
from django.conf import settings

class PageView(models.Model):
    user   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    path   = models.CharField(max_length=512)
    method = models.CharField(max_length=8)
    at     = models.DateTimeField(auto_now_add=True)
    ip     = models.GenericIPAddressField(null=True, blank=True)
    ua     = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["at"]), models.Index(fields=["path"])]
        ordering = ["-at"]
