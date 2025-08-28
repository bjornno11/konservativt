from django.urls import path
from . import views
app_name = "docs"

urlpatterns = [
    path("", views.DocumentList.as_view(), name="docs-list"),
    path("upload/", views.doc_upload, name="upload"),
    path("folder/<int:folder_id>/", views.doc_folder, name="folder"),
    path("<int:pk>/", views.DocumentDetail.as_view(), name="docs-detail"),
    path("<int:pk>/rediger/", views.DocumentUpdate.as_view(), name="docs-update"),
    path("<int:pk>/slett/", views.DocumentDelete.as_view(), name="docs-delete"),
    path("d/<int:pk>/", views.download_document, name="download"),
]
