
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse,  HttpResponseForbidden
from django.db.models import Prefetch
from geo.models import Fylke
from members.models import Lokallag, Medlem, Fylkeslagsmedlemskap
from .models import FylkeSite

def _get_fylke(slug: str) -> Fylke:
    # Bare offentlige sider er tilgjengelige uten login
    return get_object_or_404(Fylke, slug=slug, homepage_public=True)

def fylker_index(request):
    # Offentlig oversikt (kan skjules senere om ønskelig)
    fylker = Fylke.objects.filter(homepage_public=True).order_by("navn")
    return render(request, "fylkehub/index.html", {"fylker": fylker})

def fylke_home(request, slug):
    fylke = _get_fylke(slug)
    lokallag = Lokallag.objects.filter(fylke_id=fylke.id).order_by("navn")
    return render(request, "fylkehub/home.html", {
        "fylke": fylke,
        "title": fylke.homepage_title or fylke.navn,
        "intro": fylke.homepage_intro,
        "lokallag": lokallag,
    })

def fylke_lokallag(request, slug):
    fylke = _get_fylke(slug)
    lokallag = Lokallag.objects.filter(fylke_id=fylke.id).select_related("kommune").order_by("navn")
    return render(request, "fylkehub/lokallag.html", {"fylke": fylke, "lokallag": lokallag})

@login_required
def fylke_medlemmer(request, slug):
    fylke = _get_fylke(slug)
    # Tilgang: superuser ELLER har fylkesrolle via Fylkeslagsmedlemskap i dette fylket
    has_role = request.user.is_superuser or Fylkeslagsmedlemskap.objects.filter(
        medlem__user=request.user,
        fylkeslag__fylke_id=fylke.id,
    ).exists()
    if not has_role:
        return HttpResponseForbidden("Du har ikke tilgang til medlemmer i dette fylket.")
    medlemmer = (Medlem.objects
                 .filter(kommune__fylke_id=fylke.id)
                 .select_related("kommune", "kommune__fylke")
                 .order_by("etternavn", "fornavn"))
    return render(request, "fylkehub/medlemmer.html", {"fylke": fylke, "medlemmer": medlemmer})

@login_required
def fylke_docs(request, slug):
    fylke = _get_fylke(slug)
    if not _user_has_fylkesrolle(request.user, fylke):
        return HttpResponseForbidden("Du har ikke tilgang til dokumenter i dette fylket.")
    # Start enkelt: pek til docs-appen med et filter i URL/struktur senere
    return render(request, "fylkehub/docs.html", {"fylke": fylke})
