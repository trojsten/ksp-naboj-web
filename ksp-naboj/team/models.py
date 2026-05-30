import secrets

from django.db import models


def _generate_login_code():
    return secrets.token_hex(4).upper()


class Team(models.Model):
    JUNIOR = "junior"
    SENIOR = "senior"
    CATEGORY_CHOICES = [(JUNIOR, "Junior"), (SENIOR, "Senior")]

    name = models.CharField(max_length=255, unique=True)
    school = models.CharField(max_length=255)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    members = models.CharField(max_length=500)
    competition = models.ForeignKey(
        "ksp_naboj_competition.Competition", on_delete=models.CASCADE
    )
    login_code = models.CharField(
        max_length=16, default=_generate_login_code, unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.school})"


class TeamProgress(models.Model):
    team = models.OneToOneField("Team", on_delete=models.CASCADE)
    unlocked_problems = models.ManyToManyField(
        "ksp_naboj_problem.Problem", related_name="unlocked_by"
    )
    last_unlock_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    highest_unlocked_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Progress: {self.team.name}"


MEMBER_COLORS = ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"]


class TeamMemberActivity(models.Model):
    """Tracks which problem each browser session is currently editing."""

    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="activities")
    session_key = models.CharField(max_length=40)
    color_index = models.PositiveSmallIntegerField(default=0)
    current_problem = models.ForeignKey(
        "ksp_naboj_problem.Problem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("team", "session_key")

    @property
    def color(self):
        return MEMBER_COLORS[self.color_index % len(MEMBER_COLORS)]

    def __str__(self):
        return f"Member {self.color_index + 1} on {self.team.name}"
