from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Team, TeamProgress


@receiver(post_save, sender=Team)
def create_team_progress(sender, instance, created, **kwargs):
    if created:
        TeamProgress.objects.create(team=instance)
