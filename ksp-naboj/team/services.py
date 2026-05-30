import importlib

from django.utils import timezone

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress


def handle_successful_submission(submission):
    """Unlock new problems after an accepted easy submission.

    MUST be called inside transaction.atomic().
    """
    if submission.problem.difficulty != "easy" or submission.status != "accepted":
        return

    # Lock the progress row to prevent concurrent unlock races
    progress = TeamProgress.objects.select_for_update().get(team=submission.team)

    competition = submission.problem.competition
    title = submission.problem.title
    unlock_order = submission.problem.unlock_order

    # Unlock the hard variant of the same problem
    hard_problem = Problem.objects.filter(
        competition=competition,
        title=title,
        difficulty="hard",
        unlock_order=unlock_order,
    ).first()

    if hard_problem and not progress.unlocked_problems.filter(pk=hard_problem.pk).exists():
        progress.unlocked_problems.add(hard_problem)

    # Unlock the next easy problem
    next_easy = Problem.objects.filter(
        competition=competition,
        difficulty="easy",
        unlock_order=progress.highest_unlocked_order + 1,
    ).first()

    if next_easy:
        progress.unlocked_problems.add(next_easy)
        progress.highest_unlocked_order = next_easy.unlock_order

    progress.last_unlock_at = timezone.now()
    progress.save()
