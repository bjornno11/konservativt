from django.shortcuts import render
from members.models import SentralstyreMedlemskap

# Create your views here.
from django.shortcuts import render, redirect
from django.urls import reverse
from .utils import sentral_required, user_in_sentral

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
import logging
log = logging.getLogger(__name__)

@staff_member_required
def test_email(request):
    to = request.user.email or settings.DEFAULT_FROM_EMAIL
    log.info("TEST-EMAIL: sender til %s via %s:%s TLS=%s user=%s",
             to, settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_USE_TLS, settings.EMAIL_HOST_USER)
    n = send_mail("Konservativt SMTP test",
                  "Dette er en test sendt fra Gunicorn-prosessen.",
                  settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    return HttpResponse(f"OK: send_mail returnerte {n} til {to}")



@sentral_required
def dashboard(request):
    links = {
        "pending": reverse("admin:members_pendingmedlem_changelist"),
        "medlemmer": reverse("admin:members_medlem_changelist"),
        "lokallag": reverse("admin:members_lokallag_changelist"),
        "fylkeslag": reverse("admin:members_fylkeslag_changelist"),
        "docs": "/konservativt/doc/",
        "admin": reverse("admin:index"),
    }
    aktive = (SentralstyreMedlemskap.objects
              .select_related("medlem", "rolle")
              .filter(sluttdato__isnull=True)
              .order_by("rolle__rang", "medlem__etternavn", "medlem__fornavn"))
    return render(request, "sentral/dashboard.html", {"links": links, "sentral_aktive": aktive})

def post_login_router(request):
    """
    Etter innlogging send brukeren til riktig sted:
    - Sentralstyre → /sentral/
    - Ellers → admin-index (eller en annen ‘home’ om du ønsker)
    """
    u = request.user
    if u.is_authenticated and user_in_sentral(u):
        return redirect("/konservativt/sentral/")
    # Standard fallback (tilpass gjerne til ditt ønske)
    return redirect("/konservativt/admin/")
