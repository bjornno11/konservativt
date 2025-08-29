from django.shortcuts import render
from members.models import SentralstyreMedlemskap

# Create your views here.
from django.shortcuts import render, redirect
from django.urls import reverse
from .utils import sentral_required, user_in_sentral

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
