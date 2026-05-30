import importlib

Team = importlib.import_module("ksp-naboj.team.models").Team


def get_team_from_session(request):
    """Return the Team stored in session, or None."""
    team_id = request.session.get("team_id")
    if not team_id:
        return None
    try:
        return Team.objects.select_related("competition").get(pk=team_id)
    except Team.DoesNotExist:
        return None
