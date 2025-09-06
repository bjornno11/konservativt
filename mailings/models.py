from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailTemplate(models.Model):
    navn = models.CharField(max_length=200)
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    text_body = models.TextField(blank=True)
    sist_endret = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.navn

class Campaign(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Utkast"),
        ("QUEUED", "I kø"),
        ("SENDING", "Sender"),
        ("SENT", "Sendt"),
    ]
    navn = models.CharField(max_length=200)
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    opprettet_av = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    opprettet = models.DateTimeField(auto_now_add=True)

    # (kommer senere: scope/filtre per rolle – vi begynner enkelt)
    def __str__(self):
        return f"{self.navn} ({self.status})"

class Outbox(models.Model):
    """En rad per mottaker som skal sendes for en bestemt kampanje."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="outbox")
    to_email = models.EmailField()
    medlem_id = models.IntegerField(null=True, blank=True)  # valgfritt: kobling til members.Medlem.id
    sent_ok = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_try = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "to_email"], name="uniq_campaign_email")
        ]
        indexes = [
            models.Index(fields=["campaign", "sent_ok"]),
        ]

    def __str__(self):
        return f"{self.to_email} ({'ok' if self.sent_ok else 'pending'})"

class EmailLog(models.Model):
    LEVELS = [("INFO", "INFO"), ("WARN", "WARN"), ("ERR", "ERR")]
    outbox = models.ForeignKey(Outbox, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField(max_length=8, choices=LEVELS)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created:%Y-%m-%d %H:%M} {self.level}: {self.message[:60]}"
