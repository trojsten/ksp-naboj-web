from django.test import TestCase
import importlib

Competition = importlib.import_module('ksp-naboj.competition.models').Competition


class CompetitionModelTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026,
            judge_namespace='naboj-2026',
            is_active=True
        )

    def test_competition_creation(self):
        self.assertEqual(self.competition.year, 2026)
        self.assertEqual(self.competition.judge_namespace, 'naboj-2026')
        self.assertTrue(self.competition.is_active)

    def test_competition_str_representation(self):
        self.assertEqual(str(self.competition), 'Competition 2026')

    def test_competition_year_unique(self):
        with self.assertRaises(Exception):
            Competition.objects.create(
                year=2026,
                judge_namespace='naboj-2026-duplicate'
            )

    def test_competition_defaults(self):
        new_competition = Competition.objects.create(
            year=2027,
            judge_namespace='naboj-2027'
        )
        self.assertTrue(new_competition.is_active)

    def test_multiple_competitions(self):
        Competition.objects.create(
            year=2025,
            judge_namespace='naboj-2025',
            is_active=False
        )
        self.assertEqual(Competition.objects.count(), 2)
