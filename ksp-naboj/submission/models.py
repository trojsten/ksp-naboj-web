from django.db import models


class Submission(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    RUNTIME_ERROR = 'runtime_error'
    COMPILATION_ERROR = 'compilation_error'
    TIME_LIMIT_EXCEEDED = 'time_limit_exceeded'
    MEMORY_LIMIT_EXCEEDED = 'memory_limit_exceeded'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (RUNTIME_ERROR, 'Runtime Error'),
        (COMPILATION_ERROR, 'Compilation Error'),
        (TIME_LIMIT_EXCEEDED, 'Time Limit Exceeded'),
        (MEMORY_LIMIT_EXCEEDED, 'Memory Limit Exceeded'),
    ]

    team = models.ForeignKey('ksp_naboj_team.Team', on_delete=models.CASCADE)
    problem = models.ForeignKey('ksp_naboj_problem.Problem', on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=50)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=PENDING)
    execution_time = models.FloatField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    judged_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.team.name} - {self.problem.title} ({self.status})"
