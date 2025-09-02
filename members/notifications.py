# members/notifications.py
from typing import Set
import logging
from django.core.mail import send_mail
from django.conf import settings

from members.models import Fylkeslag  # <- NYTT: bruk Fylkeslag for mellomledd

logger = logging.getLogger(__name__)

def _first_nonempty(*vals):
    for v in vals:
        v = (v or "").strip()
        if v:
            return v
    return None

def _get_fylke_from_obj(obj):
    # Prøv direkte felt
    if getattr(obj, "fylke_id", None):
        return obj.fylke
    # Prøv via kommune
    if getattr(obj, "kommune_id", None) and getattr(obj, "kommune", None):
        return obj.kommune.fylke
    return None

def notify_new_self_registration(obj) -> int:
    """
    Bygger mottakerliste:
      1) Lokallag (contact_email/epost)
      2) Fylkeslag (for obj sitt fylke)  ← NY PRIORITET
      3) geo.Fylke.contact_email
      4) DEFAULT_FROM_EMAIL
    """
    recipients: Set[str] = set()

    # 1) Lokallag først
    lag_qs = getattr(obj, "lokallag", None)
    if lag_qs:
        for lag in lag_qs.all():
            email = _first_nonempty(
                getattr(lag, "contact_email", None),
                getattr(lag, "epost", None),
            )
            if email:
                recipients.add(email)

    # 2) Hvis ingen lokallag: forsøk Fylkeslag for samme fylke
    if not recipients:
        fylke = _get_fylke_from_obj(obj)
        if fylke:
            fl = (Fylkeslag.objects
                  .filter(fylke_id=fylke.id)
                  .order_by("id")
                  .first())
            if fl:
                email = _first_nonempty(
                    getattr(fl, "contact_email", None),
                    getattr(fl, "epost", None),
                )
                if email:
                    recipients.add(email)

    # 3) Hvis fortsatt tomt: geo.Fylke som fallback
    if not recipients:
        fylke = _get_fylke_from_obj(obj)
        if fylke:
            email = _first_nonempty(getattr(fylke, "contact_email", None))
            if email:
                recipients.add(email)

    # 4) Siste utvei
    if not recipients:
        recipients.add(getattr(settings, "DEFAULT_FROM_EMAIL", "bn@zc.no"))

    recipients = sorted(recipients)
    logger.info("notify_new_self_registration: mottakere=%s", recipients)

    fullnavn = f"{getattr(obj, 'fornavn', '')} {getattr(obj, 'etternavn', '')}".strip()
    linjer = [
        f"Navn: {fullnavn}",
        f"Telefon: {getattr(obj, 'telefon', '-') or '-'}",
        f"E-post: {getattr(obj, 'epost', '-') or '-'}",
    ]
    if getattr(obj, "kommune", None):
        linjer.append(f"Kommune: {obj.kommune.navn}")
    if lag_qs and lag_qs.exists():
        linjer.append("Valgte lokallag: " + ", ".join(l.navn for l in lag_qs.all()))
    else:
        linjer.append("Valgte lokallag: (ingen)")

    body = "Ny selv-registrering i Konservativt:\n\n" + "\n".join(linjer) + "\n\n" \
           "Logg inn på fylkessiden for å tildele lokallag og godkjenne det nye medlemmegt."

    return send_mail(
        subject="Ny selv-registrering",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=recipients,
        fail_silently=False,
    )
