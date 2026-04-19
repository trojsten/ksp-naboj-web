import importlib

from django.urls import path

from . import views

submit_code = importlib.import_module("ksp-naboj.submission.views").submit_code

urlpatterns = [
    path("<int:year>/", views.CompetitionDetailView.as_view(), name="competition-detail"),
    path("submit/", submit_code, name="submit-code"),
]
