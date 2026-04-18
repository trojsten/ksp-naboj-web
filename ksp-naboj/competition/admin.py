from django.contrib import admin
from .models import Competition


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('year', 'judge_namespace', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('year', 'judge_namespace')
