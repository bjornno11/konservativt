from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.auth.views import LoginView, LogoutView
from konservativt.views import Home, MyLoginView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/logout/", LogoutView.as_view(next_page=reverse_lazy("admin:index")), name="logout"),

    # Øvrige auth-URLer (inkluderer /accounts/logout/ som KREVER POST)
    path("accounts/", include("django.contrib.auth.urls")),

    # Dokumentappen under /doc/ (namespace = "docs")
    path("doc/", include(("docs.urls", "docs"), namespace="docs")),

    # Forside -> dokumentliste
#    path("", include("portal.urls")),          
    path("members/", include(("members.urls", "members"), namespace="members")),
    path("sentral/", include("sentral.urls")),      # ← NY
    path("", include("sentral.router_urls")),       # ← NY: post-login router (forklart under)
    path("fylke/", include(("fylkehub.urls", "fylkehub"), namespace="fylkehub")),
    path("lag/", include(("laghub.urls", "laghub"), namespace="laghub")),
]

# Kun i DEBUG: serve media (ev. static) fra Django
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Konservativt – Administrasjon"
admin.site.site_title = "Konservativt Admin"
admin.site.index_title = "Velkommen til administrasjonsportalen"
