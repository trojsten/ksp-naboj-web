import importlib
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

Competition = importlib.import_module("ksp-naboj.competition.models").Competition
Team = importlib.import_module("ksp-naboj.team.models").Team
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress
Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
submission_services = importlib.import_module("ksp-naboj.submission.services")


class SubmissionModelTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026, judge_namespace="naboj-2026"
        )
        self.team = Team.objects.create(
            name="Test Team",
            school="Test School",
            category="junior",
            members="Alice,Bob,Charlie,David",
            competition=self.competition,
        )
        self.problem = Problem.objects.create(
            competition=self.competition,
            title="Test Problem",
            description="Test description",
            difficulty="easy",
            unlock_order=1,
            judge_task="test_problem",
        )

    def test_submission_creation(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("hello world")',
            language="python",
        )
        self.assertEqual(submission.team, self.team)
        self.assertEqual(submission.problem, self.problem)
        self.assertEqual(submission.code, 'print("hello world")')
        self.assertEqual(submission.language, "python")
        self.assertEqual(submission.status, "pending")

    def test_submission_str_representation(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="test code",
            language="python",
            status="accepted",
        )
        self.assertEqual(
            str(submission), f"{self.team.name} - {self.problem.title} (accepted)"
        )

    def test_submission_status_choices(self):
        pending_sub = Submission.objects.create(
            team=self.team, problem=self.problem, code="pending code", language="python"
        )
        accepted_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="accepted code",
            language="python",
            status="accepted",
        )
        rejected_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="rejected code",
            language="python",
            status="rejected",
        )
        self.assertEqual(pending_sub.status, "pending")
        self.assertEqual(accepted_sub.status, "accepted")
        self.assertEqual(rejected_sub.status, "rejected")

    def test_submission_timestamps(self):
        submission = Submission.objects.create(
            team=self.team, problem=self.problem, code="test code", language="python"
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
            code="error code",
            language="python",
            status="compilation_error",
            error_message="SyntaxError: invalid syntax",
        )
        self.assertEqual(submission.error_message, "SyntaxError: invalid syntax")

    def test_submission_execution_time(self):
        submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="fast code",
            language="python",
            status="accepted",
            execution_time=0.5,
        )
        self.assertEqual(submission.execution_time, 0.5)

    def test_multiple_submissions(self):
        Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="first submission",
            language="python",
        )
        Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code="second submission",
            language="python",
            status="accepted",
        )
        self.assertEqual(Submission.objects.count(), 2)

    def test_submission_team_relationship(self):
        submission = Submission.objects.create(
            team=self.team, problem=self.problem, code="test code", language="python"
        )
        self.assertEqual(self.team.submission_set.count(), 1)
        self.assertEqual(self.team.submission_set.first(), submission)

    def test_submission_problem_relationship(self):
        submission = Submission.objects.create(
            team=self.team, problem=self.problem, code="test code", language="python"
        )
        self.assertEqual(self.problem.submission_set.count(), 1)
        self.assertEqual(self.problem.submission_set.first(), submission)

    def test_different_languages(self):
        python_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("python")',
            language="python",
        )
        cpp_sub = Submission.objects.create(
            team=self.team, problem=self.problem, code='cout << "cpp";', language="c++"
        )
        java_sub = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='System.out.println("java");',
            language="java",
        )
        self.assertEqual(python_sub.language, "python")
        self.assertEqual(cpp_sub.language, "c++")
        self.assertEqual(java_sub.language, "java")


def _make_submit(public_id="pub-1", protocol_key="proto-key-1"):
    """Build a lightweight fake object mimicking judge_client's Submit."""
    return type(
        "FakeSubmit",
        (),
        {"public_id": public_id, "protocol_key": protocol_key},
    )()


@override_settings(USE_MOCK_JUDGE=False, JUDGE_TOKEN="test-token", JUDGE_NAMESPACE="")
class SubmitToJudgeTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026, judge_namespace="naboj-2026"
        )
        self.team = Team.objects.create(
            name="Judge Team",
            school="Test School",
            category="junior",
            members="Alice,Bob",
            competition=self.competition,
        )
        self.problem = Problem.objects.create(
            competition=self.competition,
            title="Judge Problem",
            description="desc",
            difficulty="easy",
            unlock_order=1,
            judge_task="judge_problem_task",
        )
        self.submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("hi")',
            language="python",
        )

    def test_filename_for_known_language(self):
        self.assertEqual(submission_services.filename_for("python"), "solution.py")
        self.assertEqual(submission_services.filename_for("cpp"), "solution.cpp")

    def test_filename_for_unknown_language_falls_back(self):
        self.assertEqual(submission_services.filename_for("brainfuck"), "solution.txt")

    @patch.object(submission_services, "get_judge_client")
    def test_submit_to_judge_stores_public_id_and_protocol_key(self, mock_get_client):
        fake_client = mock_get_client.return_value
        fake_client.submit.return_value = _make_submit(
            public_id="pub-abc", protocol_key="key-xyz"
        )

        submission_services.submit_to_judge(self.submission, ip="10.0.0.1")

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.judge_public_id, "pub-abc")
        self.assertEqual(self.submission.protocol_key, "key-xyz")

        fake_client.submit.assert_called_once()
        kwargs = fake_client.submit.call_args.kwargs
        self.assertEqual(kwargs["task"], "judge_problem_task")
        self.assertEqual(kwargs["namespace"], "naboj-2026")
        self.assertEqual(kwargs["external_user_id"], f"team:{self.team.id}")
        self.assertEqual(kwargs["filename"], "solution.py")
        self.assertEqual(kwargs["program"], b'print("hi")')
        self.assertEqual(kwargs["ip"], "10.0.0.1")

    @patch.object(submission_services, "get_judge_client")
    def test_submit_to_judge_does_not_alter_status(self, mock_get_client):
        mock_get_client.return_value.submit.return_value = _make_submit()

        self.assertEqual(self.submission.status, Submission.PENDING)
        submission_services.submit_to_judge(self.submission)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.PENDING)

    @patch.object(submission_services, "get_judge_client")
    @override_settings(
        USE_MOCK_JUDGE=False, JUDGE_TOKEN="test-token", JUDGE_NAMESPACE="env-ns"
    )
    def test_judge_namespace_setting_overrides_competition(self, mock_get_client):
        fake_client = mock_get_client.return_value
        fake_client.submit.return_value = _make_submit()

        submission_services.submit_to_judge(self.submission)

        kwargs = fake_client.submit.call_args.kwargs
        self.assertEqual(kwargs["namespace"], "env-ns")
        # competition.judge_namespace is "naboj-2026" but must not be used
        self.assertNotEqual(kwargs["namespace"], self.competition.judge_namespace)


class _FakeVerdict:
    def __init__(self, code):
        self.code = code


class _FakeStats:
    def __init__(self, cpu_time):
        self.cpu_time = cpu_time


class _FakeTest:
    def __init__(self, cpu_time):
        self.stats = _FakeStats(cpu_time)


class _FakeProtocol:
    def __init__(self, verdict_code, cpu_times=None):
        self.final_verdict = _FakeVerdict(verdict_code) if verdict_code else None
        self.tests = [_FakeTest(t) for t in (cpu_times or [])]


class _FakeJudgeSubmit:
    """Mimics the judge_client Submit object returned by get_submit()."""

    def __init__(self, status_code, verdict_code="OK", cpu_times=None):
        self.status = status_code  # 0=QUEUED, 1=FINISHED, 2=FAILED
        self.protocol = _FakeProtocol(verdict_code, cpu_times)


@override_settings(USE_MOCK_JUDGE=False, JUDGE_TOKEN="test-token", JUDGE_NAMESPACE="")
class ApplyJudgeResultTest(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            year=2026, judge_namespace="naboj-2026"
        )
        self.team = Team.objects.create(
            name="Result Team",
            school="Test School",
            category="junior",
            members="Alice,Bob",
            competition=self.competition,
        )
        self.problem = Problem.objects.create(
            competition=self.competition,
            title="Result Problem",
            description="desc",
            difficulty="easy",
            unlock_order=1,
            judge_task="result_problem_task",
        )
        self.submission = Submission.objects.create(
            team=self.team,
            problem=self.problem,
            code='print("hi")',
            language="python",
            judge_public_id="pub-existing",
        )

    @patch.object(submission_services, "handle_successful_submission")
    def test_ok_verdict_maps_to_accepted_and_unlocks(self, mock_unlock):
        submit = _FakeJudgeSubmit(1, "OK", cpu_times=[42, 58])

        submission_services.apply_judge_result(self.submission, submit)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.ACCEPTED)
        self.assertEqual(self.submission.execution_time, 0.058)
        self.assertEqual(self.submission.error_message, "")
        self.assertIsNotNone(self.submission.judged_at)
        mock_unlock.assert_called_once_with(self.submission)

    @patch.object(submission_services, "handle_successful_submission")
    def test_wa_verdict_maps_to_rejected_no_unlock(self, mock_unlock):
        submit = _FakeJudgeSubmit(1, "WA", cpu_times=[10])

        submission_services.apply_judge_result(self.submission, submit)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.REJECTED)
        self.assertEqual(self.submission.error_message, "WA")
        mock_unlock.assert_not_called()

    @patch.object(submission_services, "handle_successful_submission")
    def test_tle_verdict_maps_correctly(self, mock_unlock):
        submit = _FakeJudgeSubmit(1, "TLE")

        submission_services.apply_judge_result(self.submission, submit)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.TIME_LIMIT_EXCEEDED)
        mock_unlock.assert_not_called()

    @patch.object(submission_services, "handle_successful_submission")
    def test_apply_is_idempotent_for_unlock(self, mock_unlock):
        submit = _FakeJudgeSubmit(1, "OK", cpu_times=[100])

        submission_services.apply_judge_result(self.submission, submit)
        # second call (e.g. from a repeated poll) must not unlock again
        submission_services.apply_judge_result(self.submission, submit)

        mock_unlock.assert_called_once()

    @patch.object(submission_services, "handle_successful_submission")
    def test_partial_pok_does_not_unlock(self, mock_unlock):
        submit = _FakeJudgeSubmit(1, "POK")

        submission_services.apply_judge_result(self.submission, submit)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.REJECTED)
        mock_unlock.assert_not_called()

    @patch.object(submission_services, "get_judge_client")
    def test_refresh_skips_queued_submit(self, mock_get_client):
        mock_get_client.return_value.get_submit.return_value = _FakeJudgeSubmit(0)
        original_status = self.submission.status

        submission_services.refresh_from_judge(self.submission)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, original_status)

    @patch.object(submission_services, "handle_successful_submission")
    @patch.object(submission_services, "get_judge_client")
    def test_refresh_applies_finished_submit(self, mock_get_client, mock_unlock):
        mock_get_client.return_value.get_submit.return_value = _FakeJudgeSubmit(
            1, "OK", cpu_times=[20]
        )

        submission_services.refresh_from_judge(self.submission)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.ACCEPTED)
        mock_unlock.assert_called_once()

    @patch.object(submission_services, "get_judge_client")
    def test_refresh_noop_when_already_judged(self, mock_get_client):
        self.submission.status = Submission.ACCEPTED
        self.submission.save()

        submission_services.refresh_from_judge(self.submission)

        mock_get_client.return_value.get_submit.assert_not_called()
