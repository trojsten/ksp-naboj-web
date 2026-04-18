import importlib

Problem = importlib.import_module('ksp-naboj.problem.models').Problem


def handle_successful_submission(submission):
    if submission.problem.difficulty == 'easy':
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
        
        unlocked_easy_problems = progress.unlocked_problems.filter(difficulty='easy')
        highest_unlocked_order = unlocked_easy_problems.order_by('-unlock_order').first()
        
        if highest_unlocked_order:
            next_easy = Problem.objects.filter(
                competition=competition,
                difficulty='easy',
                unlock_order__gt=highest_unlocked_order.unlock_order
            ).order_by('unlock_order').first()
        else:
            next_easy = Problem.objects.filter(
                competition=competition,
                difficulty='easy'
            ).order_by('unlock_order').first()
        
        if next_easy and next_easy not in progress.unlocked_problems.all():
            progress.unlocked_problems.add(next_easy)
        
        progress.save()
