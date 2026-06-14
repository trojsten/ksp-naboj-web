import importlib

from django.urls import path

from . import views

submit_code = importlib.import_module("ksp-naboj.submission.views").submit_code
submission_status = importlib.import_module(
    "ksp-naboj.submission.views"
).submission_status

urlpatterns = [
    path(
        "<int:year>/",
        views.CompetitionDetailView.as_view(),
        name="competition-detail",
    ),
    path("submit/", submit_code, name="submit-code"),
    path(
        "status/<str:judge_public_id>/",
        submission_status,
        name="submission-status",
    ),
    path(
        "<int:year>/problems/",
        views.ProblemListPartialView.as_view(),
        name="problem-list-partial",
    ),
    path("activity/", views.report_activity, name="report-activity"),
    path("<int:year>/sse/", views.sse_stream, name="sse-stream"),
]
