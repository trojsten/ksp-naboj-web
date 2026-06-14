import importlib

from django.conf import settings
from django.db import transaction
from django.utils import timezone

Submission = importlib.import_module("ksp-naboj.submission.models").Submission
handle_successful_submission = importlib.import_module(
    "ksp-naboj.team.services"
).handle_successful_submission

_judge_client = None

LANGUAGE_EXTENSIONS = {
    "python": "py",
    "cpp": "cpp",
    "c": "c",
    "java": "java",
    "javascript": "js",
    "typescript": "ts",
    "rust": "rs",
    "go": "go",
    "pascal": "pas",
    "php": "php",
    "ruby": "rb",
    "csharp": "cs",
    "kotlin": "kt",
    "scala": "scala",
    "haskell": "hs",
}

VERDICT_TO_STATUS = {
    "OK": Submission.ACCEPTED,
    "WA": Submission.REJECTED,
    "TLE": Submission.TIME_LIMIT_EXCEEDED,
    "EXC": Submission.RUNTIME_ERROR,
    "CEX": Submission.COMPILATION_ERROR,
    "MEM": Submission.MEMORY_LIMIT_EXCEEDED,
    "PRV": Submission.REJECTED,
    "POK": Submission.REJECTED,
    "SEX": Submission.REJECTED,
    "IGN": Submission.REJECTED,
    "CONNERR": Submission.REJECTED,
}


def get_judge_client():
    global _judge_client
    if _judge_client is None:
        from judge_client.client import JudgeClient

        _judge_client = JudgeClient(settings.JUDGE_TOKEN, settings.JUDGE_URL)
    return _judge_client


def filename_for(language: str) -> str:
    ext = LANGUAGE_EXTENSIONS.get(language, "txt")
    return f"solution.{ext}"


def submit_to_judge(submission, ip: str | None = None):
    problem = submission.problem
    team = submission.team
    competition = problem.competition
    namespace = settings.JUDGE_NAMESPACE or competition.judge_namespace

    client = get_judge_client()
    submit = client.submit(
        task=problem.judge_task,
        external_user_id=f"team:{team.id}",
        filename=filename_for(submission.language),
        program=submission.code.encode(),
        ip=ip,
        namespace=namespace,
    )

    submission.judge_public_id = submit.public_id
    submission.protocol_key = submit.protocol_key
    submission.save(update_fields=["judge_public_id", "protocol_key"])
    return submission


def refresh_from_judge(submission) -> "Submission":
    """Fetch the current state of a submission from the judge and apply it.

    No-op when the submission has no judge public id or is no longer pending.
    Silently catches judge errors so polling never 500s.
    """
    if not submission.judge_public_id or submission.status != Submission.PENDING:
        return submission

    client = get_judge_client()
    try:
        submit = client.get_submit(submission.judge_public_id)
    except Exception:
        return submission

    if getattr(submit, "status", None) is None:
        return submission

    # SubmitStatus.FINISHED == the protocol is ready
    if _submit_status_code(submit.status) != 1:
        return submission

    return apply_judge_result(submission, submit)


def apply_judge_result(submission, submit) -> "Submission":
    """Map a finished judge Submit onto our Submission and unlock if accepted.

    Idempotent: safe to call multiple times (unlock only fires the first time).
    """
    protocol = getattr(submit, "protocol", None)
    verdict_code = _verdict_code(getattr(protocol, "final_verdict", None))
    new_status = VERDICT_TO_STATUS.get(verdict_code, Submission.REJECTED)
    was_accepted = submission.status == Submission.ACCEPTED

    submission.status = new_status
    submission.judged_at = timezone.now()
    submission.execution_time = _max_cpu_time_seconds(protocol)
    submission.error_message = (
        "" if new_status == Submission.ACCEPTED else (verdict_code or "Rejected")
    )
    submission.save()

    if new_status == Submission.ACCEPTED and not was_accepted:
        with transaction.atomic():
            handle_successful_submission(submission)

    return submission


def _submit_status_code(status) -> int | None:
    # SubmitStatus members expose .status (0/1/2); tolerate plain ints/strings
    code = getattr(status, "status", status)
    try:
        return int(code)
    except (TypeError, ValueError):
        return None


def _verdict_code(verdict) -> str | None:
    if verdict is None:
        return None
    code = getattr(verdict, "code", None)
    if code is not None:
        return code
    return str(verdict)


def _max_cpu_time_seconds(protocol) -> float | None:
    tests = getattr(protocol, "tests", None) or []
    times = []
    for test in tests:
        stats = getattr(test, "stats", None)
        cpu = getattr(stats, "cpu_time", None) if stats else None
        if cpu is not None:
            times.append(cpu)
    if not times:
        return None
    return round(max(times) / 1000, 3)
