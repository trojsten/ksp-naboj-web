from django.test import TestCase
from django.utils import timezone
import importlib

Competition = importlib.import_module('ksp-naboj.competition.models').Competition
Team = importlib.import_module('ksp-naboj.team.models').Team
TeamProgress = importlib.import_module('ksp-naboj.team.models').TeamProgress
Problem = importlib.import_module('ksp-naboj.problem.models').Problem
Submission = importlib.import_module('ksp-naboj.submission.models').Submission
handle_successful_submission = importlib.import_module('ksp-naboj.team.services').handle_successful_submission


class ProgressiveUnlockTest(TestCase):
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

        self.problem1_easy = Problem.objects.create(
            competition=self.competition,
            title='Two Sums',
            description='First problem',
            difficulty='easy',
            unlock_order=1,
            judge_task='two-sums_a'
        )
        self.problem1_hard = Problem.objects.create(
            competition=self.competition,
            title='Two Sums',
            description='First problem hard',
            difficulty='hard',
            unlock_order=1,
            judge_task='two-sums_b'
        )
        self.problem2_easy = Problem.objects.create(
            competition=self.competition,
            title='Three Sums',
            description='Second problem',
            difficulty='easy',
            unlock_order=2,
            judge_task='three-sums_a'
        )
        self.problem2_hard = Problem.objects.create(
            competition=self.competition,
            title='Three Sums',
            description='Second problem hard',
            difficulty='hard',
            unlock_order=2,
            judge_task='three-sums_b'
        )

    def test_initial_unlocked_problems(self):
        # First 2 problems are unlocked initially (since only 2 exist with unlock_order <= 6)
        self.team_progress.refresh_from_db()
        self.assertEqual(self.team_progress.unlocked_problems.count(), 2)
        self.assertIn(self.problem1_easy, self.team_progress.unlocked_problems.all())
        self.assertIn(self.problem2_easy, self.team_progress.unlocked_problems.all())
        self.assertEqual(self.team_progress.highest_unlocked_order, 2)

    def test_unlock_first_easy_problem(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        unlocked = list(self.team_progress.unlocked_problems.all())

        # 1_easy, 2_easy already unlocked, now 1_hard should be added
        self.assertEqual(len(unlocked), 3)
        self.assertIn(self.problem1_easy, unlocked)
        self.assertIn(self.problem2_easy, unlocked)
        self.assertIn(self.problem1_hard, unlocked)

    def test_unlock_second_easy_problem(self):
        # Manually reset to only have 1_easy unlocked (simulating before solve)
        self.team_progress.unlocked_problems.set([self.problem1_easy])
        self.team_progress.highest_unlocked_order = 1
        self.team_progress.save()

        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem2_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        unlocked = list(self.team_progress.unlocked_problems.all())

        # 1_easy was already unlocked, solving 2_easy unlocks 2_hard
        self.assertIn(self.problem1_easy, unlocked)
        self.assertIn(self.problem2_easy, unlocked)
        self.assertIn(self.problem2_hard, unlocked)

    def test_unlock_only_on_easy_submission(self):
        hard_submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_hard,
            code='hard solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(hard_submission)

        self.team_progress.refresh_from_db()
        # Still has initial 2 problems
        self.assertEqual(self.team_progress.unlocked_problems.count(), 2)

    def test_unlock_rejected_submission(self):
        rejected_submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='wrong solution',
            language='python',
            status='rejected',
            judged_at=timezone.now()
        )
        handle_successful_submission(rejected_submission)

        self.team_progress.refresh_from_db()
        # Still has initial 2 problems
        self.assertEqual(self.team_progress.unlocked_problems.count(), 2)

    def test_unlock_pending_submission(self):
        pending_submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution',
            language='python',
            status='pending'
        )
        handle_successful_submission(pending_submission)

        self.team_progress.refresh_from_db()
        # Still has initial 2 problems
        self.assertEqual(self.team_progress.unlocked_problems.count(), 2)

    def test_multiple_unlocks_sequential(self):
        submission1 = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution1',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission1)

        self.team_progress.refresh_from_db()
        # Initial 2 + 1_hard = 3
        self.assertEqual(self.team_progress.unlocked_problems.count(), 3)

        submission2 = Submission.objects.create(
            team=self.team,
            problem=self.problem2_easy,
            code='solution2',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission2)

        self.team_progress.refresh_from_db()
        unlocked = list(self.team_progress.unlocked_problems.all())
        self.assertIn(self.problem1_easy, unlocked)
        self.assertIn(self.problem1_hard, unlocked)
        self.assertIn(self.problem2_easy, unlocked)
        self.assertIn(self.problem2_hard, unlocked)
        self.assertEqual(self.team_progress.unlocked_problems.count(), 4)

    def test_no_next_easy_problem(self):
        Problem.objects.create(
            competition=self.competition,
            title='Last Problem',
            description='Last easy problem',
            difficulty='easy',
            unlock_order=10,
            judge_task='last_problem_a'
        )

        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        unlocked = list(self.team_progress.unlocked_problems.all())

        # Initial 2 + 1_hard = 3 (next easy would be order 3, but doesn't exist yet)
        self.assertEqual(len(unlocked), 3)
        self.assertIn(self.problem1_hard, unlocked)
        self.assertIn(self.problem2_easy, unlocked)

    def test_no_hard_version_exists(self):
        # Delete the hard version to test what happens when it doesn't exist
        self.problem1_hard.delete()

        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        unlocked = list(self.team_progress.unlocked_problems.all())

        # Initial 2 (1_easy, 2_easy), no hard version to add
        self.assertEqual(len(unlocked), 2)

    def test_unlock_already_unlocked_problems(self):
        self.team_progress.unlocked_problems.add(self.problem1_hard)
        self.team_progress.save()

        initial_count = self.team_progress.unlocked_problems.count()

        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        self.assertEqual(self.team_progress.unlocked_problems.count(), initial_count)

    def test_unlock_different_teams(self):
        team2 = Team.objects.create(
            name='Test Team 2',
            school='Test School 2',
            category='senior',
            members='Eve,Frank,Grace,Heidi',
            competition=self.competition
        )
        team2_progress = team2.teamprogress

        submission1 = Submission.objects.create(
            team=self.team,
            problem=self.problem1_easy,
            code='solution1',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission1)

        self.team_progress.refresh_from_db()
        team2_progress.refresh_from_db()

        # team1: initial 2 + 1_hard = 3
        self.assertEqual(self.team_progress.unlocked_problems.count(), 3)
        # team2: still initial 2
        self.assertEqual(team2_progress.unlocked_problems.count(), 2)

    def test_highest_unlocked_order_increment(self):
        self.team_progress.refresh_from_db()
        self.assertEqual(self.team_progress.highest_unlocked_order, 2)

        problem3_easy = Problem.objects.create(
            competition=self.competition,
            title='Four Sums',
            description='Third problem',
            difficulty='easy',
            unlock_order=3,
            judge_task='four-sums_a'
        )

        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem2_easy,
            code='solution',
            language='python',
            status='accepted',
            judged_at=timezone.now()
        )
        handle_successful_submission(submission)

        self.team_progress.refresh_from_db()
        self.assertEqual(self.team_progress.highest_unlocked_order, 3)
        self.assertIn(problem3_easy, self.team_progress.unlocked_problems.all())
