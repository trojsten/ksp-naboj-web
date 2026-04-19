from django.urls import path

from . import views

urlpatterns = [
    path("<int:year>/", views.CompetitionDetailView.as_view(), name="competition-detail"),
]
