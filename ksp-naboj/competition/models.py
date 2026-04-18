from django.db import models


class Competition(models.Model):
    year = models.IntegerField(unique=True)
    judge_namespace = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Competition {self.year}"
