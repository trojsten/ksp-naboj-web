import importlib
import json
import random

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
Team = importlib.import_module("ksp-naboj.team.models").Team
handle_successful_submission = importlib.import_module(
    "ksp-naboj.team.services"
).handle_successful_submission


@csrf_exempt
@require_http_methods(["POST"])
def submit_code(request):
    data = json.loads(request.body)
    problem_id = data.get("problem_id")
    code = data.get("code", "")
    language = data.get("language", "python")
    team_id = data.get("team_id")

    if not all([problem_id, code, team_id]):
        return JsonResponse({"error": "Missing required fields"}, status=400)

    try:
        problem = Problem.objects.get(pk=problem_id)
    except Problem.DoesNotExist:
        return JsonResponse({"error": "Problem not found"}, status=404)

    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        return JsonResponse({"error": "Team not found"}, status=404)

    submission = Submission.objects.create(
        team=team,
        problem=problem,
        code=code,
        language=language,
        status=Submission.PENDING,
    )

    mock_statuses = [
        Submission.ACCEPTED,
        Submission.REJECTED,
        Submission.RUNTIME_ERROR,
        Submission.COMPILATION_ERROR,
        Submission.TIME_LIMIT_EXCEEDED,
    ]
    weights = [0.8, 0.1/2, 0.1/2, 0.1/2, 0.1/2]
    result_status = random.choices(mock_statuses, weights=weights, k=1)[0]

    submission.status = result_status
    submission.execution_time = round(random.uniform(0.01, 2.0), 3)
    submission.judged_at = timezone.now()

    if result_status != Submission.ACCEPTED:
        messages = {
            Submission.REJECTED: "Wrong answer on test case 3",
            Submission.RUNTIME_ERROR: "RuntimeError: division by zero",
            Submission.COMPILATION_ERROR: "SyntaxError: invalid syntax",
            Submission.TIME_LIMIT_EXCEEDED: "Time limit exceeded on test case 5",
        }
        submission.error_message = messages.get(result_status, "Unknown error")

    submission.save()

    if submission.status == Submission.ACCEPTED:
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
