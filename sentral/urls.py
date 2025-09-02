from django.urls import path
from . import views

from django.urls import path
from .views import test_email

app_name = "sentral"


urlpatterns = [
    path("test-email/", test_email, name="test-email"),
    path("", views.dashboard, name="dashboard"),
]

