from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.urls import reverse
from .utils import sentral_required, user_in_sentral

@sentral_required
def dashboard(request):
    # Pekere til relevante admin-sider/flows
    links = {
        "pending": reverse("admin:members_pendingmedlem_changelist"),
        "medlemmer": reverse("admin:members_medlem_changelist"),
        "lokallag": reverse("admin:members_lokallag_changelist"),
        "fylkeslag": reverse("admin:members_fylkeslag_changelist"),
        "docs": "/konservativt/doc/",
        "admin": reverse("admin:index"),
    }
    return render(request, "sentral/dashboard.html", {"links": links})

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
