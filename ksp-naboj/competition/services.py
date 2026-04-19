import importlib
from collections import OrderedDict

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission


def get_problem_groups(competition, team):
    progress = team.teamprogress if hasattr(team, "teamprogress") else None
    max_order = progress.highest_unlocked_order if progress else 0

    problems = list(
        Problem.objects.filter(
            competition=competition, unlock_order__lte=max_order
        ).order_by("unlock_order", "difficulty")
    )

    unlocked_ids = set(progress.unlocked_problems.values_list("id", flat=True)) if progress else set()

    solved_ids = set(
        Submission.objects.filter(
            team=team, status=Submission.ACCEPTED
        ).values_list("problem_id", flat=True)
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
        entry = {
            "problem": problem,
            "unlocked": is_unlocked,
            "solved": is_solved,
        }
        if problem.difficulty == Problem.EASY:
            groups[key]["easy"] = entry
        else:
            groups[key]["hard"] = entry

    return list(groups.values())


def get_unlocked_problems_json(competition, team):
    progress = team.teamprogress if hasattr(team, "teamprogress") else None
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
