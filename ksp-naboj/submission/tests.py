from django.test import TestCase
from django.utils import timezone
import importlib

Competition = importlib.import_module('ksp-naboj.competition.models').Competition
Team = importlib.import_module('ksp-naboj.team.models').Team
TeamProgress = importlib.import_module('ksp-naboj.team.models').TeamProgress
Problem = importlib.import_module('ksp-naboj.problem.models').Problem
Submission = importlib.import_module('ksp-naboj.submission.models').Submission


class SubmissionModelTest(TestCase):
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
        self.problem = Problem.objects.create(
            competition=self.competition,
            title='Test Problem',
            description='Test description',
            difficulty='easy',
            unlock_order=1,
            judge_task='test_problem'
        )

    def test_submission_creation(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("hello world")',
            language='python'
        )
        self.assertEqual(submission.team, self.team)
        self.assertEqual(submission.problem, self.problem)
        self.assertEqual(submission.code, 'print("hello world")')
        self.assertEqual(submission.language, 'python')
        self.assertEqual(submission.status, 'pending')

    def test_submission_str_representation(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='test code',
            language='python',
            status='accepted'
        )
        self.assertEqual(str(submission), f'{self.team.name} - {self.problem.title} (accepted)')

    def test_submission_status_choices(self):
        pending_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='pending code',
            language='python'
        )
        accepted_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='accepted code',
            language='python',
            status='accepted'
        )
        rejected_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='rejected code',
            language='python',
            status='rejected'
        )
        self.assertEqual(pending_sub.status, 'pending')
        self.assertEqual(accepted_sub.status, 'accepted')
        self.assertEqual(rejected_sub.status, 'rejected')

    def test_submission_timestamps(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='test code',
            language='python'
        )
        self.assertIsNotNone(submission.submitted_at)
        self.assertIsNone(submission.judged_at)
        
        submission.judged_at = timezone.now()
        submission.save()
        self.assertIsNotNone(submission.judged_at)

    def test_submission_error_message(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='error code',
            language='python',
            status='compilation_error',
            error_message='SyntaxError: invalid syntax'
        )
        self.assertEqual(submission.error_message, 'SyntaxError: invalid syntax')

    def test_submission_execution_time(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='fast code',
            language='python',
            status='accepted',
            execution_time=0.5
        )
        self.assertEqual(submission.execution_time, 0.5)

    def test_multiple_submissions(self):
        Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='first submission',
            language='python'
        )
        Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='second submission',
            language='python',
            status='accepted'
        )
        self.assertEqual(Submission.objects.count(), 2)

    def test_submission_team_relationship(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='test code',
            language='python'
        )
        self.assertEqual(self.team.submission_set.count(), 1)
        self.assertEqual(self.team.submission_set.first(), submission)

    def test_submission_problem_relationship(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='test code',
            language='python'
        )
        self.assertEqual(self.problem.submission_set.count(), 1)
        self.assertEqual(self.problem.submission_set.first(), submission)

    def test_different_languages(self):
        python_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("python")',
            language='python'
        )
        cpp_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='cout << "cpp";',
            language='c++'
        )
        java_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='System.out.println("java");',
            language='java'
        )
        self.assertEqual(python_sub.language, 'python')
        self.assertEqual(cpp_sub.language, 'c++')
        self.assertEqual(java_sub.language, 'java')
