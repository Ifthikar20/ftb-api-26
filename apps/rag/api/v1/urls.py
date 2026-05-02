from django.urls import path

from apps.rag.api.v1 import views

urlpatterns = [
    path(
        "<uuid:website_id>/sources/",
        views.KnowledgeSourceListView.as_view(),
        name="rag-source-list",
    ),
    path(
        "<uuid:website_id>/sources/<uuid:source_id>/",
        views.KnowledgeSourceDetailView.as_view(),
        name="rag-source-detail",
    ),
    path(
        "<uuid:website_id>/retrieve/",
        views.RetrieveView.as_view(),
        name="rag-retrieve",
    ),
]
