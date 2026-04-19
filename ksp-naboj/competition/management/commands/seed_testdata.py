import importlib

from django.core.management.base import BaseCommand

Competition = importlib.import_module("ksp-naboj.competition.models").Competition
Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Team = importlib.import_module("ksp-naboj.team.models").Team
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress
Submission = importlib.import_module("ksp-naboj.submission.models").Submission

PROBLEM_DATA = [
    (1, "Faktorial"),
    (2, "Sortovanie"),
    (3, "Prvocisla"),
    (4, "Fibonacci"),
    (5, "Palindrom"),
    (6, "Matice"),
    (7, "Grafy"),
    (8, "Dynamika"),
]


class Command(BaseCommand):
    help = "Seed test data: competition, problems (easy+hard), team, and progress"

    def handle(self, *args, **options):
        competition, _ = Competition.objects.get_or_create(
            year=2026,
            defaults={"judge_namespace": "naboj-2026", "is_active": True},
        )
        self.stdout.write(f"Competition: {competition}")

        for order, title in PROBLEM_DATA:
            for difficulty in ("easy", "hard"):
                suffix = "a" if difficulty == "easy" else "b"
                Problem.objects.get_or_create(
                    competition=competition,
                    title=title,
                    difficulty=difficulty,
                    defaults={
                        "unlock_order": order,
                        "judge_task": f"naboj-2026-{order}{suffix}",
                        "description": f"# {title} \n\nToto je **{difficulty}** verzia ulohy {order}.",
                    },
                )
        self.stdout.write(f"Created {len(PROBLEM_DATA) * 2} problems")

        team, _ = Team.objects.get_or_create(
            name="Test Team",
            defaults={
                "school": "Gymnazium Test",
                "category": "junior",
                "members": "Alice, Bob, Charlie, Diana",
                "competition": competition,
            },
        )
        self.stdout.write(f"Team: {team}")

        progress, _ = TeamProgress.objects.get_or_create(
            team=team,
            defaults={"score": 0, "highest_unlocked_order": 6},
        )

        easy_problems = Problem.objects.filter(
            competition=competition, difficulty="easy", unlock_order__lte=6
        )
        hard_1 = Problem.objects.get(
            competition=competition, title="Faktorial", difficulty="hard"
        )
        hard_2 = Problem.objects.get(
            competition=competition, title="Sortovanie", difficulty="hard"
        )
        for p in list(easy_problems) + [hard_1, hard_2]:
            progress.unlocked_problems.add(p)
        progress.save()
        self.stdout.write(f"Unlocked {progress.unlocked_problems.count()} problems")

        easy_1 = Problem.objects.get(
            competition=competition, title="Faktorial", difficulty="easy"
        )
        Submission.objects.get_or_create(
            team=team,
            problem=easy_1,
            language="python",
            defaults={
                "code": "print('hello')",
                "status": "accepted",
            },
        )
        self.stdout.write("Marked Faktorial easy as accepted")

        self.stdout.write(self.style.SUCCESS(f"\nDone! Visit: /competition/2026/?team_id={team.id}"))
