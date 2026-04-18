from django.contrib import admin
from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('team', 'problem', 'language', 'status', 'submitted_at', 'judged_at')
    list_filter = ('status', 'language', 'submitted_at')
    search_fields = ('team__name', 'problem__title', 'language')
    readonly_fields = ('submitted_at',)
