# portal/urls.py
from django.urls import path
from .views import SentralDashboard, FylkeDashboard, LokallagDashboard

app_name = "portal"

urlpatterns = [
    path("sentral/", SentralDashboard.as_view(), name="sentral"),
    path("fylke/<slug:slug>/", FylkeDashboard.as_view(), name="fylke"),
    path("lokal/<slug:slug>/", LokallagDashboard.as_view(), name="lokal"),
]
