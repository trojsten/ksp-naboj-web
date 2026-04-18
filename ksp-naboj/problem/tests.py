from django.test import TestCase
import importlib

Competition = importlib.import_module('ksp-naboj.competition.models').Competition
Problem = importlib.import_module('ksp-naboj.problem.models').Problem


class ProblemModelTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026,
            judge_namespace='naboj-2026'
        )

    def test_problem_creation(self):
        problem = Problem.objects.create(
            competition=self.competition,
            title='Two Sums',
            description='Test problem description',
            difficulty='easy',
            unlock_order=1,
            judge_task='two-sums_a'
        )
        self.assertEqual(problem.title, 'Two Sums')
        self.assertEqual(problem.difficulty, 'easy')
        self.assertEqual(problem.unlock_order, 1)

    def test_problem_str_representation(self):
        problem = Problem.objects.create(
            competition=self.competition,
            title='Test Problem',
            description='Description',
            difficulty='hard',
            unlock_order=2,
            judge_task='test_problem'
        )
        self.assertEqual(str(problem), 'Test Problem (hard)')

    def test_problem_difficulty_choices(self):
        easy_problem = Problem.objects.create(
            competition=self.competition,
            title='Easy Problem',
            description='Easy description',
            difficulty='easy',
            unlock_order=1,
            judge_task='easy_problem'
        )
        hard_problem = Problem.objects.create(
            competition=self.competition,
            title='Hard Problem',
            description='Hard description',
            difficulty='hard',
            unlock_order=1,
            judge_task='hard_problem'
        )
        self.assertEqual(easy_problem.difficulty, 'easy')
        self.assertEqual(hard_problem.difficulty, 'hard')

    def test_problem_judge_task_unique(self):
        Problem.objects.create(
            competition=self.competition,
            title='First Problem',
            description='First description',
            difficulty='easy',
            unlock_order=1,
            judge_task='unique_task'
        )
        with self.assertRaises(Exception):
            Problem.objects.create(
                competition=self.competition,
                title='Second Problem',
                description='Second description',
                difficulty='hard',
                unlock_order=2,
                judge_task='unique_task'
            )

    def test_problem_unique_constraint_competition_title_difficulty(self):
        Problem.objects.create(
            competition=self.competition,
            title='Two Sums',
            description='First version',
            difficulty='easy',
            unlock_order=1,
            judge_task='two-sums_a'
        )
        Problem.objects.create(
            competition=self.competition,
            title='Two Sums',
            description='Second version',
            difficulty='hard',
            unlock_order=1,
            judge_task='two-sums_b'
        )
        with self.assertRaises(Exception):
            Problem.objects.create(
                competition=self.competition,
                title='Two Sums',
                description='Duplicate easy',
                difficulty='easy',
                unlock_order=2,
                judge_task='two-sums_a_duplicate'
            )

    def test_problem_competition_relationship(self):
        problem = Problem.objects.create(
            competition=self.competition,
            title='Test Problem',
            description='Test description',
            difficulty='easy',
            unlock_order=1,
            judge_task='test_problem'
        )
        self.assertEqual(problem.competition, self.competition)
        self.assertEqual(self.competition.problem_set.count(), 1)

    def test_problem_language_optional(self):
        problem_with_language = Problem.objects.create(
            competition=self.competition,
            title='C++ Problem',
            description='C++ specific problem',
            difficulty='easy',
            unlock_order=1,
            judge_task='cpp_problem',
            language='c++'
        )
        problem_without_language = Problem.objects.create(
            competition=self.competition,
            title='Python Problem',
            description='Python problem',
            difficulty='easy',
            unlock_order=2,
            judge_task='python_problem'
        )
        self.assertEqual(problem_with_language.language, 'c++')
        self.assertIsNone(problem_without_language.language)

    def test_multiple_problems_same_unlock_order(self):
        Problem.objects.create(
            competition=self.competition,
            title='Problem A',
            description='Problem A description',
            difficulty='easy',
            unlock_order=1,
            judge_task='problem_a'
        )
        Problem.objects.create(
            competition=self.competition,
            title='Problem B',
            description='Problem B description',
            difficulty='easy',
            unlock_order=1,
            judge_task='problem_b'
        )
        self.assertEqual(Problem.objects.filter(unlock_order=1).count(), 2)

    def test_problem_ordering(self):
        Problem.objects.create(
            competition=self.competition,
            title='First Problem',
            description='First',
            difficulty='easy',
            unlock_order=3,
            judge_task='first_problem'
        )
        Problem.objects.create(
            competition=self.competition,
            title='Second Problem',
            description='Second',
            difficulty='easy',
            unlock_order=1,
            judge_task='second_problem'
        )
        Problem.objects.create(
            competition=self.competition,
            title='Third Problem',
            description='Third',
            difficulty='easy',
            unlock_order=2,
            judge_task='third_problem'
        )
        ordered_problems = Problem.objects.filter(difficulty='easy').order_by('unlock_order')
        self.assertEqual(ordered_problems[0].title, 'Second Problem')
        self.assertEqual(ordered_problems[1].title, 'Third Problem')
        self.assertEqual(ordered_problems[2].title, 'First Problem')
