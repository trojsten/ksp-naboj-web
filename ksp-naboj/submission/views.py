import importlib
import json
import random

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress
get_team_from_session = importlib.import_module(
    "ksp-naboj.team.middleware"
).get_team_from_session
handle_successful_submission = importlib.import_module(
    "ksp-naboj.team.services"
).handle_successful_submission


@require_http_methods(["POST"])
def submit_code(request):
    # Auth: team from session
    team = get_team_from_session(request)
    if not team:
        return JsonResponse({"error": "Not logged in"}, status=403)

    # Parse JSON body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    problem_id = data.get("problem_id")
    code = data.get("code", "")
    language = data.get("language", "python")

    if not problem_id or not code.strip():
        return JsonResponse({"error": "Missing problem_id or code"}, status=400)

    # Fetch problem
    try:
        problem = Problem.objects.get(pk=problem_id)
    except Problem.DoesNotExist:
        return JsonResponse({"error": "Problem not found"}, status=404)

    # Validate competition time window
    competition = team.competition
    now = timezone.now()
    if competition.end_at and now > competition.end_at:
        return JsonResponse({"error": "Competition has ended"}, status=403)

    # Validate problem is unlocked for this team
    try:
        progress = team.teamprogress
    except TeamProgress.DoesNotExist:
        return JsonResponse({"error": "Team has no progress record"}, status=400)

    if not progress.unlocked_problems.filter(pk=problem.pk).exists():
        return JsonResponse({"error": "Problem is locked"}, status=403)

    # Create submission
    submission = Submission.objects.create(
        team=team,
        problem=problem,
        code=code,
        language=language,
        status=Submission.PENDING,
    )

    # Mock judging (replace with real judge-client later)
    mock_statuses = [
        Submission.ACCEPTED,
        Submission.REJECTED,
        Submission.RUNTIME_ERROR,
        Submission.COMPILATION_ERROR,
        Submission.TIME_LIMIT_EXCEEDED,
    ]
    weights = [0.8, 0.05, 0.05, 0.05, 0.05]
    result_status = random.choices(mock_statuses, weights=weights, k=1)[0]

    submission.status = result_status
    submission.execution_time = round(random.uniform(0.01, 2.0), 3)
    submission.judged_at = timezone.now()

    if result_status != Submission.ACCEPTED:
        error_messages = {
            Submission.REJECTED: "Wrong answer on test case 3",
            Submission.RUNTIME_ERROR: "RuntimeError: division by zero",
            Submission.COMPILATION_ERROR: "SyntaxError: invalid syntax",
            Submission.TIME_LIMIT_EXCEEDED: "Time limit exceeded on test case 5",
        }
        submission.error_message = error_messages.get(result_status, "Unknown error")

    submission.save()

    # Handle accepted: unlock new problems (with locking)
    if submission.status == Submission.ACCEPTED:
        with transaction.atomic():
            handle_successful_submission(submission)

    return JsonResponse(
        {
            "submission_id": submission.id,
            "status": submission.status,
            "execution_time": submission.execution_time,
            "error_message": submission.error_message,
            "problem_title": problem.title,
            "problem_difficulty": problem.difficulty,
        }
    )
