import importlib

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import Team

Competition = importlib.import_module("ksp-naboj.competition.models").Competition


def team_login(request):
    """Simple login: team_id + login_code -> store in session -> redirect."""
    error = None

    if request.method == "POST":
        team_id = request.POST.get("team_id", "").strip()
        login_code = request.POST.get("login_code", "").strip().upper()

        if not team_id or not login_code:
            error = "Please fill in both fields."
        else:
            try:
                team = Team.objects.select_related("competition").get(
                    pk=team_id, login_code=login_code
                )
            except (Team.DoesNotExist, ValueError):
                error = "Invalid team ID or login code."
            else:
                request.session["team_id"] = team.id
                request.session["competition_year"] = team.competition.year
                return HttpResponseRedirect(
                    reverse(
                        "competition-detail",
                        kwargs={"year": team.competition.year},
                    )
                )

    return render(request, "team/login.html", {"error": error})


def team_logout(request):
    request.session.flush()
    return HttpResponseRedirect("/")
