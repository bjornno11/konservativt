# members/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PendingMedlem
from .notifications import notify_new_self_registration

logger = logging.getLogger(__name__)

@receiver(post_save, sender=PendingMedlem)
def pendingmedlem_created(sender, instance, created, **kwargs):
    if not created:
        return
    # Fjern evt. verve_kilde-filter inntil vi vet feltet finnes
    try:
        notify_new_self_registration(instance)
        logger.info("Varsel sendt for PendingMedlem id=%s", instance.id)
    except Exception:
        logger.exception("Varsel ved ny registrering feilet (id=%s)", getattr(instance, "id", "?"))
