from django.urls import path
from .views import post_login_router

urlpatterns = [
    path("home/", post_login_router, name="post_login_router"),
]
