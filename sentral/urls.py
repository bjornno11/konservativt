from django.urls import path
from . import views

app_name = "sentral"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
