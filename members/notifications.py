from typing import Set
from django.core.mail import send_mail
from django.conf import settings

def _first_nonempty(*vals):
    for v in vals:
        v = (v or "").strip()
        if v:
            return v
    return None

def notify_new_self_registration(pending) -> int:
    """
    Varsle riktig mottaker ved self-registrering:
      - Hvis ett/flere lokallag valgt: send til hvert lag sin epost (contact_email eller epost).
      - Ellers: send til fylkets contact_email (via pending.fylke eller pending.kommune.fylke).
      - Fallback: DEFAULT_FROM_EMAIL.
    Returnerer antall utsendte eposter.
    """
    recipients: Set[str] = set()

    # 1) Lokallag først
    lag_qs = getattr(pending, "lokallag", None)
    if lag_qs:
        for lag in lag_qs.all():
            # støtt begge feltnavn på Lokallag
            email = _first_nonempty(getattr(lag, "contact_email", None),
                                    getattr(lag, "epost", None))
            if email:
                recipients.add(email)

    # 2) Hvis ingen lokallag: finn fylke
    if not recipients:
        fylke = None
        if getattr(pending, "fylke_id", None):
            fylke = pending.fylke
        elif getattr(pending, "kommune_id", None) and pending.kommune:
            fylke = pending.kommune.fylke

        if fylke:
            email = _first_nonempty(getattr(fylke, "contact_email", None))
            if email:
                recipients.add(email)

    # 3) Fallback
    if not recipients:
        recipients.add(getattr(settings, "DEFAULT_FROM_EMAIL", "bn@zc.no"))

    fullnavn = f"{pending.fornavn} {pending.etternavn}".strip()
    lines = [
        f"Navn: {fullnavn}",
        f"Telefon: {pending.telefon or '-'}",
        f"E-post: {pending.epost or '-'}",
    ]
    if getattr(pending, "kommune", None):
        lines.append(f"Kommune: {pending.kommune.navn}")

    if lag_qs and lag_qs.exists():
        lines.append("Valgte lokallag: " + ", ".join(l.navn for l in lag_qs.all()))
    else:
        lines.append("Valgte lokallag: (ingen)")

    body = (
        "Ny selv-registrering i Konservativt:\n\n"
        + "\n".join(lines)
        + "\n\nLogg inn i admin for å godkjenne og tildele lokallag."
    )

    return send_mail(
        subject="Ny selv-registrering",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=sorted(recipients),
        fail_silently=False,
    )
