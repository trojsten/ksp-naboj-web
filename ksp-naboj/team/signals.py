from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Team, TeamProgress
import importlib

Problem = importlib.import_module('ksp-naboj.problem.models').Problem


@receiver(post_save, sender=Team)
def create_team_progress(sender, instance, created, **kwargs):
    if created:
        progress = TeamProgress.objects.create(team=instance)

        # Unlock first 6 easy problems
        initial_problems = Problem.objects.filter(
            competition=instance.competition,
            difficulty='easy',
            unlock_order__lte=6
        )

        if initial_problems.exists():
            progress.unlocked_problems.add(*initial_problems)
            max_order = max(p.unlock_order for p in initial_problems)
            progress.highest_unlocked_order = max_order
            progress.save()


@receiver(post_save, sender=Problem)
def unlock_problem_for_teams(sender, instance, created, **kwargs):
    if created and instance.difficulty == 'easy' and instance.unlock_order <= 6:
        # Unlock this problem for all teams in the same competition
        for progress in TeamProgress.objects.filter(team__competition=instance.competition):
            if instance not in progress.unlocked_problems.all():
                progress.unlocked_problems.add(instance)
                # Update highest_unlocked_order if needed
                if instance.unlock_order > progress.highest_unlocked_order:
                    progress.highest_unlocked_order = instance.unlock_order
                progress.save()
