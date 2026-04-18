from django.test import TestCase
import importlib

Competition = importlib.import_module('ksp-naboj.competition.models').Competition
Team = importlib.import_module('ksp-naboj.team.models').Team
TeamProgress = importlib.import_module('ksp-naboj.team.models').TeamProgress


class TeamModelTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026,
            judge_namespace='naboj-2026'
        )
        self.team = Team.objects.create(
            name='Test Team',
            school='Test School',
            category='junior',
            members='Alice,Bob,Charlie,David',
            competition=self.competition
        )

    def test_team_creation(self):
        self.assertEqual(self.team.name, 'Test Team')
        self.assertEqual(self.team.school, 'Test School')
        self.assertEqual(self.team.category, 'junior')
        self.assertEqual(self.team.members, 'Alice,Bob,Charlie,David')

    def test_team_str_representation(self):
        self.assertEqual(str(self.team), 'Test Team (Test School)')

    def test_team_category_choices(self):
        junior_team = Team.objects.create(
            name='Junior Team',
            school='School A',
            category='junior',
            members='Alice,Bob,Charlie,David',
            competition=self.competition
        )
        senior_team = Team.objects.create(
            name='Senior Team',
            school='School B',
            category='senior',
            members='Eve,Frank,Grace,Heidi',
            competition=self.competition
        )
        self.assertEqual(junior_team.category, 'junior')
        self.assertEqual(senior_team.category, 'senior')

    def test_team_name_unique(self):
        with self.assertRaises(Exception):
            Team.objects.create(
                name='Test Team',
                school='Different School',
                category='senior',
                members='Eve,Frank,Grace,Heidi',
                competition=self.competition
            )

    def test_team_competition_relationship(self):
        self.assertEqual(self.team.competition, self.competition)
        self.assertEqual(self.competition.team_set.count(), 1)

    def test_team_members_string_format(self):
        team_with_more_members = Team.objects.create(
            name='Large Team',
            school='School C',
            category='junior',
            members='Alice,Bob,Charlie,David,Eve,Frank',
            competition=self.competition
        )
        self.assertIn(',', team_with_more_members.members)


class TeamProgressModelTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026,
            judge_namespace='naboj-2026'
        )
        self.team = Team.objects.create(
            name='Test Team',
            school='Test School',
            category='junior',
            members='Alice,Bob,Charlie,David',
            competition=self.competition
        )
        self.team_progress = self.team.teamprogress

    def test_team_progress_auto_creation(self):
        self.assertIsNotNone(self.team_progress)
        self.assertEqual(self.team_progress.team, self.team)

    def test_team_progress_initial_state(self):
        self.assertEqual(self.team_progress.score, 0)
        self.assertIsNone(self.team_progress.last_unlock_at)
        self.assertEqual(self.team_progress.unlocked_problems.count(), 0)

    def test_team_progress_str_representation(self):
        self.assertEqual(str(self.team_progress), f'TeamProgress object ({self.team_progress.id})')

    def test_team_progress_team_relationship(self):
        self.assertEqual(self.team_progress.team, self.team)
        self.assertEqual(self.team.teamprogress, self.team_progress)

    def test_multiple_teams_have_separate_progress(self):
        team2 = Team.objects.create(
            name='Test Team 2',
            school='Test School 2',
            category='senior',
            members='Eve,Frank,Grace,Heidi',
            competition=self.competition
        )
        progress2 = team2.teamprogress
        
        self.assertNotEqual(self.team_progress.id, progress2.id)
        self.assertEqual(self.team_progress.team, self.team)
        self.assertEqual(progress2.team, team2)
