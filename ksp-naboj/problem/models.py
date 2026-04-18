from django.db import models


class Problem(models.Model):
    EASY = 'easy'
    HARD = 'hard'
    DIFFICULTY_CHOICES = [(EASY, 'Easy'), (HARD, 'Hard')]

    competition = models.ForeignKey('ksp_naboj_competition.Competition', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    unlock_order = models.PositiveIntegerField()
    judge_task = models.CharField(max_length=100, unique=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('competition', 'title', 'difficulty')

    def __str__(self):
        return f"{self.title} ({self.difficulty})"
