from django.db import models


class Team(models.Model):
    JUNIOR = 'junior'
    SENIOR = 'senior'
    CATEGORY_CHOICES = [(JUNIOR, 'Junior'), (SENIOR, 'Senior')]

    name = models.CharField(max_length=255, unique=True)
    school = models.CharField(max_length=255)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    members = models.CharField(max_length=500)
    competition = models.ForeignKey('ksp_naboj_competition.Competition', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.school})"


class TeamProgress(models.Model):
    team = models.OneToOneField('Team', on_delete=models.CASCADE)
    unlocked_problems = models.ManyToManyField('ksp_naboj_problem.Problem', related_name='unlocked_by')
    last_unlock_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    highest_unlocked_order = models.PositiveIntegerField(default=0)
