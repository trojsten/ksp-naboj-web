import importlib
import json
import logging
import random

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from judge_client.exceptions import (
    JudgeConnectionError,
    TaskNotFoundError,
    UnknownLanguageError,
)

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress
get_team_from_session = importlib.import_module(
    "ksp-naboj.team.middleware"
).get_team_from_session
handle_successful_submission = importlib.import_module(
    "ksp-naboj.team.services"
).handle_successful_submission
submit_to_judge = importlib.import_module(
    "ksp-naboj.submission.services"
).submit_to_judge
refresh_from_judge = importlib.import_module(
    "ksp-naboj.submission.services"
).refresh_from_judge

logger = logging.getLogger("ksp-naboj")


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

    if settings.USE_MOCK_JUDGE:
        result_status, execution_time, error_message = _mock_judge()
        submission.status = result_status
        submission.execution_time = execution_time
        submission.judged_at = timezone.now()
        submission.error_message = error_message
        submission.save()

        if submission.status == Submission.ACCEPTED:
            with transaction.atomic():
                handle_successful_submission(submission)
    else:
        try:
            submit_to_judge(submission, ip=request.META.get("REMOTE_ADDR"))
        except Exception as exc:
            http_status, message = _classify_judge_error(exc, problem)
            logger.warning(
                "Judge submit failed for problem pk=%s (judge_task=%r, "
                "namespace=%r): %r",
                problem.pk,
                problem.judge_task,
                settings.JUDGE_NAMESPACE or problem.competition.judge_namespace,
                exc,
                exc_info=True,
            )
            submission.status = Submission.REJECTED
            submission.error_message = message
            submission.judged_at = timezone.now()
            submission.save()
            return JsonResponse(
                {
                    "submission_id": submission.id,
                    "status": submission.status,
                    "error_message": submission.error_message,
                    "problem_title": problem.title,
                    "problem_difficulty": problem.difficulty,
                },
                status=http_status,
            )

    return JsonResponse(
        {
            "submission_id": submission.id,
            "judge_public_id": submission.judge_public_id,
            "status": submission.status,
            "execution_time": submission.execution_time,
            "error_message": submission.error_message,
            "problem_title": problem.title,
            "problem_difficulty": problem.difficulty,
        }
    )


@require_http_methods(["GET"])
def submission_status(request, judge_public_id):
    team = get_team_from_session(request)
    if not team:
        return JsonResponse({"error": "Not logged in"}, status=403)

    try:
        submission = Submission.objects.get(judge_public_id=judge_public_id, team=team)
    except Submission.DoesNotExist:
        return JsonResponse({"error": "Submission not found"}, status=404)

    if not settings.USE_MOCK_JUDGE and submission.status == Submission.PENDING:
        try:
            refresh_from_judge(submission)
        except Exception as exc:
            logger.warning(
                "Failed to refresh submission pk=%s from judge: %r",
                submission.pk,
                exc,
                exc_info=True,
            )
        submission.refresh_from_db()

    return JsonResponse(
        {
            "submission_id": submission.id,
            "status": submission.status,
            "execution_time": submission.execution_time,
            "error_message": submission.error_message,
        }
    )


def _classify_judge_error(exc, problem):
    if isinstance(exc, TaskNotFoundError):
        return 422, f"Judge task not found: '{problem.judge_task}'."
    if isinstance(exc, UnknownLanguageError):
        return 422, "Could not detect the programming language for this submission."
    if isinstance(exc, JudgeConnectionError):
        return 502, f"Judge is unavailable: {exc}"
    return 502, f"Failed to submit to judge: {exc}"


def _mock_judge():
    mock_statuses = [
        Submission.ACCEPTED,
        Submission.REJECTED,
        Submission.RUNTIME_ERROR,
        Submission.COMPILATION_ERROR,
        Submission.TIME_LIMIT_EXCEEDED,
    ]
    weights = [0.8, 0.05, 0.05, 0.05, 0.05]
    result_status = random.choices(mock_statuses, weights=weights, k=1)[0]

    execution_time = round(random.uniform(0.01, 2.0), 3)

    error_messages = {
        Submission.REJECTED: "Wrong answer on test case 3",
        Submission.RUNTIME_ERROR: "RuntimeError: division by zero",
        Submission.COMPILATION_ERROR: "SyntaxError: invalid syntax",
        Submission.TIME_LIMIT_EXCEEDED: "Time limit exceeded on test case 5",
    }
    if result_status != Submission.ACCEPTED:
        error_message = error_messages.get(result_status, "")
    else:
        error_message = ""

    return result_status, execution_time, error_message
