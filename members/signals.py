# members/signals.py
import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PendingMedlem
from .notifications import notify_new_self_registration

log = logging.getLogger(__name__)

@receiver(post_save, sender=PendingMedlem)  # korrekt bruk: ingen lister her
def pendingmedlem_created(sender, instance, created, **kwargs):
    if not created:
        return

    def _send():
        try:
            sent = notify_new_self_registration(instance)
            log.info("Varsel sendt for PendingMedlem id=%s (antall=%s)", instance.id, sent)
        except Exception:
            log.exception("Varsel feilet (id=%s)", getattr(instance, "id", "?"))

    # Send etter DB-commit (M2M ferdig)
    transaction.on_commit(_send)
