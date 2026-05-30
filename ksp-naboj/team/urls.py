from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.team_login, name="team-login"),
    path("logout/", views.team_logout, name="team-logout"),
]
