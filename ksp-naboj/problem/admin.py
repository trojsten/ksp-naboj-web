from django.contrib import admin
from .models import Problem


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'unlock_order', 'judge_task', 'competition')
    list_filter = ('difficulty', 'competition')
    search_fields = ('title', 'judge_task')
