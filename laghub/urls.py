from django.urls import path
from . import views

app_name = "laghub"

urlpatterns = [
    path("", views.lag_index, name="index"),                       # /lag/
    path("<slug:slug>/", views.lag_home, name="home"),             # /lag/<lokallag-slug>/
    path("<slug:slug>/medlemmer/", views.lag_medlemmer, name="medlemmer"),  # beskyttet
    path("<slug:slug>/dokumenter/", views.lag_docs, name="docs"),           # beskyttet (placeholder)
]
