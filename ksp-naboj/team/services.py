import importlib

Problem = importlib.import_module('ksp-naboj.problem.models').Problem


def handle_successful_submission(submission):
    if submission.problem.difficulty == 'easy' and submission.status == 'accepted':
        progress = submission.team.teamprogress

        competition = submission.problem.competition
        title = submission.problem.title
        unlock_order = submission.problem.unlock_order

        hard_problem = Problem.objects.filter(
            competition=competition,
            title=title,
            difficulty='hard',
            unlock_order=unlock_order
        ).first()

        if hard_problem and hard_problem not in progress.unlocked_problems.all():
            progress.unlocked_problems.add(hard_problem)

        next_easy = Problem.objects.filter(
            competition=competition,
            difficulty='easy',
            unlock_order=progress.highest_unlocked_order + 1
        ).first()

        if next_easy:
            progress.unlocked_problems.add(next_easy)
            progress.highest_unlocked_order = next_easy.unlock_order

        progress.save()
