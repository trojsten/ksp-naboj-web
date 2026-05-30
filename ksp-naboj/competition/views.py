import importlib
import json
import time
from datetime import timedelta

from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from .models import Competition
from .services import get_problem_groups, get_unlocked_problems_json

get_team_from_session = importlib.import_module(
    "ksp-naboj.team.middleware"
).get_team_from_session
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
TeamMemberActivity = importlib.import_module(
    "ksp-naboj.team.models"
).TeamMemberActivity
MEMBER_COLORS = importlib.import_module("ksp-naboj.team.models").MEMBER_COLORS


def _get_activities(team):
    """Return active team member activities (seen in the last 60s)."""
    cutoff = timezone.now() - timedelta(seconds=60)
    return list(
        TeamMemberActivity.objects.filter(team=team, last_seen__gte=cutoff)
        .select_related("current_problem")
    )


def _ensure_activity(request, team):
    """Get or create the TeamMemberActivity for this session."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    activity, created = TeamMemberActivity.objects.get_or_create(
        team=team,
        session_key=session_key,
        defaults={
            "color_index": TeamMemberActivity.objects.filter(team=team).count()
            % len(MEMBER_COLORS)
        },
    )
    if not created:
        # Touch last_seen
        activity.save(update_fields=["last_seen"])
    return activity


class CompetitionDetailView(TemplateView):
    template_name = "competition/competition.html"

    def dispatch(self, request, *args, **kwargs):
        self.team = get_team_from_session(request)
        if not self.team:
            return HttpResponseRedirect(reverse("team-login"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)

        _ensure_activity(self.request, self.team)
        activities = _get_activities(self.team)

        problem_groups = get_problem_groups(competition, self.team, activities)
        problems_json = json.dumps(
            get_unlocked_problems_json(competition, self.team)
        )

        context["competition"] = competition
        context["team"] = self.team
        context["problem_groups"] = problem_groups
        context["problems_json"] = problems_json
        return context


class ProblemListPartialView(TemplateView):
    """htmx partial: returns the problem list HTML + OOB JSON data update."""

    template_name = "competition/partials/_problem_list.html"

    def get(self, request, *args, **kwargs):
        self.team = get_team_from_session(request)
        if not self.team:
            return HttpResponse("", status=204)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)
        activities = _get_activities(self.team)
        context["problem_groups"] = get_problem_groups(
            competition, self.team, activities
        )
        context["problems_json"] = json.dumps(
            get_unlocked_problems_json(competition, self.team)
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        """Append an OOB swap to update the problems JSON data."""
        response = super().render_to_response(context, **response_kwargs)
        response.render()
        oob_html = (
            '<script type="application/json" id="problems-data"'
            f' hx-swap-oob="true">{context["problems_json"]}</script>'
        )
        response.content = response.content + oob_html.encode()
        return response


# ---------- SSE + Activity endpoints ----------


@require_http_methods(["POST"])
def report_activity(request):
    """Called when a user selects a problem. Updates their activity record."""
    team = get_team_from_session(request)
    if not team:
        return JsonResponse({"error": "Not logged in"}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    problem_id = data.get("problem_id")

    activity = _ensure_activity(request, team)
    activity.current_problem_id = problem_id
    activity.save(update_fields=["current_problem_id", "last_seen"])

    return JsonResponse({"ok": True})


def sse_stream(request, year):
    """Server-Sent Events stream. Pushes problem list HTML whenever state changes."""
    team = get_team_from_session(request)
    if not team:
        return HttpResponse("Not logged in", status=403)

    competition = get_object_or_404(Competition, year=year)

    def event_stream():
        last_hash = None
        while True:
            activities = _get_activities(team)
            problem_groups = get_problem_groups(competition, team, activities)
            problems_json = json.dumps(
                get_unlocked_problems_json(competition, team)
            )

            # Render the problem list HTML
            html = render_to_string(
                "competition/partials/_problem_list.html",
                {"problem_groups": problem_groups},
            )

            # Simple change detection: hash the rendered content
            current_hash = hash((html, problems_json))
            if current_hash != last_hash:
                last_hash = current_hash

                # Escape newlines for SSE data format
                escaped_html = html.replace("\n", "\ndata: ")
                yield f"event: problem-list\ndata: {escaped_html}\n\n"

                yield f"event: problems-json\ndata: {problems_json}\n\n"

            time.sleep(3)

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
