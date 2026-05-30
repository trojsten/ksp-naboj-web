import importlib
from collections import OrderedDict

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress

# Short labels for submission statuses shown in the problem list
STATUS_LABELS = {
    "accepted": "OK",
    "rejected": "WA",
    "runtime_error": "RE",
    "compilation_error": "CE",
    "time_limit_exceeded": "TLE",
    "memory_limit_exceeded": "MLE",
    "pending": "...",
}


def get_problem_groups(competition, team, activities=None):
    # Always fetch fresh from DB to avoid stale cached relations (critical for SSE)
    progress = TeamProgress.objects.filter(team=team).first()
    max_order = progress.highest_unlocked_order if progress else 0

    problems = list(
        Problem.objects.filter(
            competition=competition, unlock_order__lte=max_order
        ).order_by("unlock_order", "difficulty")
    )

    unlocked_ids = (
        set(progress.unlocked_problems.values_list("id", flat=True))
        if progress
        else set()
    )

    solved_ids = set(
        Submission.objects.filter(team=team, status=Submission.ACCEPTED).values_list(
            "problem_id", flat=True
        )
    )

    # Get the LAST submission per problem for this team
    last_submissions = {}
    for sub in (
        Submission.objects.filter(team=team)
        .order_by("-submitted_at")
        .values("problem_id", "status")
    ):
        # First seen per problem_id wins (most recent due to ordering)
        if sub["problem_id"] not in last_submissions:
            last_submissions[sub["problem_id"]] = sub["status"]

    # Build activity map: problem_id -> list of {color, color_index}
    activity_map = {}
    if activities:
        for act in activities:
            if act.current_problem_id:
                activity_map.setdefault(act.current_problem_id, []).append(
                    {"color": act.color, "index": act.color_index}
                )

    groups = OrderedDict()
    for problem in problems:
        key = (problem.unlock_order, problem.title)
        if key not in groups:
            groups[key] = {
                "title": problem.title,
                "unlock_order": problem.unlock_order,
                "easy": None,
                "hard": None,
            }
        is_unlocked = problem.id in unlocked_ids
        is_solved = problem.id in solved_ids

        last_status = last_submissions.get(problem.id)
        entry = {
            "problem": problem,
            "unlocked": is_unlocked,
            "solved": is_solved,
            "last_status": STATUS_LABELS.get(last_status, "") if last_status else "",
            "last_status_raw": last_status or "",
            "teammates": activity_map.get(problem.id, []),
        }
        if problem.difficulty == Problem.EASY:
            groups[key]["easy"] = entry
        else:
            groups[key]["hard"] = entry

    return list(groups.values())


def get_unlocked_problems_json(competition, team):
    # Always fetch fresh from DB to avoid stale cached relations (critical for SSE)
    progress = TeamProgress.objects.filter(team=team).first()
    if not progress:
        return {}

    unlocked = progress.unlocked_problems.filter(
        competition=competition
    ).select_related("competition")

    return {
        str(p.id): {
            "title": p.title,
            "difficulty": p.difficulty,
            "description": p.description,
            "language": p.language or "",
        }
        for p in unlocked
    }
