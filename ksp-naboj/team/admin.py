from django.contrib import admin
from .models import Team, TeamProgress


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'category', 'competition', 'created_at')
    list_filter = ('category', 'competition')
    search_fields = ('name', 'school')


@admin.register(TeamProgress)
class TeamProgressAdmin(admin.ModelAdmin):
    list_display = ('team', 'score', 'last_unlock_at')
    list_filter = ('last_unlock_at',)
    search_fields = ('team__name',)
