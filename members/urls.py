# members/urls.py
from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # CRUD
    path("", views.MembersList.as_view(), name="list"),
    path("new/", views.MemberCreate.as_view(), name="new"),
    path("<int:pk>/", views.MemberDetail.as_view(), name="detail"),
    path("<int:pk>/edit/", views.MemberUpdate.as_view(), name="edit"),

    # Godkjenning
    path("pending/", views.PendingList.as_view(), name="pending"),
    path("<int:pk>/approve/", views.MemberApprove.as_view(), name="approve"),
    path("approve/", views.ApproveBulk.as_view(), name="approve-bulk"),

    # Hjelpe-endepunkter
    path("hx/kommuner/",   views.HxKommuner.as_view(),   name="hx-kommuner"),
    path("hx/lokallag/",   views.HxLokallag.as_view(),   name="hx-lokallag"),
    path("hx/postnummer/", views.HxPostnummer.as_view(), name="hx-postnummer"),
    path("api/postnummer/", views.ApiPostnummer.as_view(), name="api-postnummer"),
    path("join/", views.SelfRegister.as_view(), name="self-register"),
    path("join/thanks/", views.SelfThanks.as_view(), name="self-thanks"),

]
