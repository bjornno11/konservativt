# 

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.db.models import Prefetch
from members.models import Lokallag, Medlem, Medlemskap

def _get_lag(slug: str) -> Lokallag:
    # Om du har et "public"-flagg på lokallag senere, filtrer på det her
    return get_object_or_404(Lokallag, slug=slug)

def lag_index(request):
    # En enkel oversikt over alle lag, evt. filtrer på fylke via ?fylke=<id>
    qs = Lokallag.objects.select_related("fylke", "kommune").order_by("fylke__navn", "navn")
    fylke_id = request.GET.get("fylke")
    if fylke_id and str(fylke_id).isdigit():
        qs = qs.filter(fylke_id=int(fylke_id))
    return render(request, "laghub/index.html", {"lag": qs})

def lag_home(request, slug):
    lag = _get_lag(slug)
    return render(request, "laghub/home.html", {"lag": lag})

def lag_home(request, slug):
    lag = get_object_or_404(Lokallag, slug=slug)
    return render(request, "laghub/lag_home.html", {"lag": lag})

@login_required
def lag_medlemmer(request, slug):
    lag = _get_lag(slug)
    # Tilgang: superuser ELLER er medlem som har Medlemskap i dette laget
    has_access = request.user.is_superuser or Medlemskap.objects.filter(
        medlem__user=request.user, lokallag_id=lag.id
    ).exists()
    if not has_access:
        return HttpResponseForbidden("Du har ikke tilgang til dette lokallaget.")

    medlemmer = (Medlem.objects
                 .filter(lokallag__id=lag.id)
                 .select_related("kommune", "kommune__fylke")
                 .order_by("etternavn", "fornavn")
                 .distinct())
    return render(request, "laghub/medlemmer.html", {"lag": lag, "medlemmer": medlemmer})

@login_required
def lag_docs(request, slug):
    lag = _get_lag(slug)
    # Samme tilgangsregel som over
    has_access = request.user.is_superuser or Medlemskap.objects.filter(
        medlem__user=request.user, lokallag_id=lag.id
    ).exists()
    if not has_access:
        return HttpResponseForbidden("Du har ikke tilgang til dette lokallaget.")
    # Placeholder – kobles til docs-appen senere
    return render(request, "laghub/docs.html", {"lag": lag})
