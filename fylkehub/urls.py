from django.urls import path
from . import views

app_name = "fylkehub"

urlpatterns = [
    path("", views.fylker_index, name="index"),                 # /konservativt/fylke/
    path("<slug:slug>/", views.fylke_home, name="home"),        # /konservativt/fylke/<fylke-slug>/
    path("<slug:slug>/lokallag/", views.fylke_lokallag, name="lokallag"),
    path("<slug:slug>/medlemmer/", views.fylke_medlemmer, name="medlemmer"),  # beskyttet
    path("<slug:slug>/dokumenter/", views.fylke_docs, name="docs"),           # enkel start
]
