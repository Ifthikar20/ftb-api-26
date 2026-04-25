from django.urls import path

from . import views

urlpatterns = [
    path("suggest/", views.CompetitorSuggestView.as_view(), name="competitor-suggest"),
    path("<uuid:website_id>/", views.CompetitorListView.as_view(), name="competitor-list"),
    path("<uuid:website_id>/discover/", views.CompetitorDiscoverView.as_view(), name="competitor-discover"),
    path("<uuid:website_id>/compare/", views.CompetitorCompareView.as_view(), name="competitor-compare"),
    path("<uuid:website_id>/changes/", views.CompetitorChangesView.as_view(), name="competitor-changes"),
    path("<uuid:website_id>/<uuid:comp_id>/", views.CompetitorDetailView.as_view(), name="competitor-detail"),
]
