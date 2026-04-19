import importlib
import json

from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from .models import Competition
from .services import get_problem_groups, get_unlocked_problems_json

Team = importlib.import_module("ksp-naboj.team.models").Team


class CompetitionDetailView(TemplateView):
    template_name = "competition/competition.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)

        team_id = self.request.GET.get("team_id")
        if team_id:
            team = get_object_or_404(Team, pk=team_id, competition=competition)
        else:
            team = None

        problem_groups = []
        problems_json = "{}"
        if team:
            problem_groups = get_problem_groups(competition, team)
            problems_json = json.dumps(get_unlocked_problems_json(competition, team))

        context["competition"] = competition
        context["team"] = team
        context["problem_groups"] = problem_groups
        context["problems_json"] = problems_json
        return context
