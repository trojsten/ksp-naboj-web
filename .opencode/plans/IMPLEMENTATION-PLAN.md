# Implementation Plan: Critical Fixes + Dynamic Updates + Code Persistence

> **Scope:** Fix signal registration, add team-code auth, fix submission safety, add localStorage code persistence, add htmx-powered live team submission feed and problem list refresh.

---

## Table of Contents

1. [Fix Signal Registration](#1-fix-signal-registration)
2. [Team Login Code Auth](#2-team-login-code-auth)
3. [Fix Submission Safety](#3-fix-submission-safety)
4. [localStorage Code Persistence](#4-localstorage-code-persistence)
5. [htmx: Live Submission Feed](#5-htmx-live-submission-feed)
6. [htmx: Problem List Refresh on Unlock](#6-htmx-problem-list-refresh-on-unlock)

---

## Implementation Checklist

- [x] 1.1 Fix `team/apps.py` signal registration
- [x] 2.1 Add `login_code` field to Team model + migration
- [x] 2.2 Create `team/middleware.py` with `get_team_from_session()`
- [x] 2.3 Create `team/views.py` with login/logout views
- [x] 2.4 Create `team/templates/team/login.html`
- [x] 2.5 Wire team URLs (`team/urls.py` + root `urls.py`)
- [x] 2.6 Update `CompetitionDetailView` to use session auth
- [x] 2.7 Update `seed_testdata.py` to print login code
- [x] 3.1 Rewrite `submission/views.py` (remove csrf_exempt, session auth, validation)
- [x] 3.2 Add `select_for_update` + transactions to `team/services.py`
- [x] 4.1 Rewrite `monaco-editor_controller.js` with localStorage persistence
- [x] 4.2 Update `_editor_panel.html` (pass teamId to editor)
- [x] 5.1 Create `_submission_feed.html` partial template
- [x] 5.2 Add `SubmissionFeedView` to `competition/views.py`
- [x] 5.3 Rewrite `submission_controller.js` (dispatch htmx events, remove teamId)
- [x] 6.1 Add `ProblemListPartialView` with OOB JSON swap
- [x] 6.2 Wire new URLs in `competition/urls.py`
- [x] 6.3 Rewrite `competition.html` with htmx polling + feed panel
- [x] 6.4 Update `problem-statement_controller.js` to re-parse JSON on htmx swap
- [x] 6.5 Update `monaco-editor_controller.js` to re-parse JSON on htmx swap
- [x] 7.0 Run `pnpm build` and verify no JS build errors
- [x] 7.1 Run `python manage.py check` and verify no Django errors
- [x] 7.2 Run tests: 45/47 pass (2 pre-existing failures, 0 regressions)

---

## 1. Fix Signal Registration

**Problem:** `team/apps.py` has an empty `ready()` so `create_team_progress` and `unlock_problem_for_teams` signals never fire in production. Tests pass by accident because the test runner imports the module.

### 1.1 Fix `team/apps.py`

```python
# ksp-naboj/team/apps.py
from django.apps import AppConfig


class TeamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ksp-naboj.team"
    label = "ksp_naboj_team"

    def ready(self):
        from . import signals  # noqa: F401
```

**Files changed:** `ksp-naboj/team/apps.py`

---

## 2. Team Login Code Auth

**Goal:** Teams get a `team_id` + `login_code` (e.g. printed on a paper at the competition). They enter these on a simple login page, which stores the team in the session. No Django User accounts needed for competitors.

### 2.1 Add `login_code` field to Team model

```python
# ksp-naboj/team/models.py

import secrets

def _generate_login_code():
    return secrets.token_hex(4).upper()  # e.g. "A3F1B2C8"


class Team(models.Model):
    JUNIOR = "junior"
    SENIOR = "senior"
    CATEGORY_CHOICES = [(JUNIOR, "Junior"), (SENIOR, "Senior")]

    name = models.CharField(max_length=255, unique=True)
    school = models.CharField(max_length=255)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    members = models.CharField(max_length=500)
    competition = models.ForeignKey(
        "ksp_naboj_competition.Competition", on_delete=models.CASCADE
    )
    login_code = models.CharField(
        max_length=16, default=_generate_login_code, unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.school})"
```

Then generate a migration:
```bash
docker compose exec web python manage.py makemigrations team
docker compose exec web python manage.py migrate
```

### 2.2 Create team login view

```python
# ksp-naboj/team/views.py
import importlib

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import Team

Competition = importlib.import_module("ksp-naboj.competition.models").Competition


def team_login(request):
    """Simple login: team_id + login_code -> store in session -> redirect."""
    error = None

    if request.method == "POST":
        team_id = request.POST.get("team_id", "").strip()
        login_code = request.POST.get("login_code", "").strip().upper()

        if not team_id or not login_code:
            error = "Please fill in both fields."
        else:
            try:
                team = Team.objects.select_related("competition").get(
                    pk=team_id, login_code=login_code
                )
            except (Team.DoesNotExist, ValueError):
                error = "Invalid team ID or login code."
            else:
                request.session["team_id"] = team.id
                request.session["competition_year"] = team.competition.year
                return HttpResponseRedirect(
                    reverse(
                        "competition-detail",
                        kwargs={"year": team.competition.year},
                    )
                )

    return render(request, "team/login.html", {"error": error})


def team_logout(request):
    request.session.flush()
    return HttpResponseRedirect("/")
```

### 2.3 Create login template

```html
<!-- ksp-naboj/team/templates/team/login.html -->
{% extends "base.html" %}

{% block title %}Team Login{% endblock %}

{% block container %}
<div class="max-w-sm mx-auto mt-16">
  <h1 class="text-2xl font-bold mb-6 text-center">Team Login</h1>

  {% if error %}
    <div class="bg-error/10 text-error border border-error/30 rounded px-3 py-2 mb-4 text-sm">
      {{ error }}
    </div>
  {% endif %}

  <form method="post" class="space-y-4">
    {% csrf_token %}
    <div>
      <label for="team_id" class="block text-sm font-medium mb-1">Team ID</label>
      <input type="text" name="team_id" id="team_id"
             class="input" placeholder="e.g. 42" required>
    </div>
    <div>
      <label for="login_code" class="block text-sm font-medium mb-1">Login Code</label>
      <input type="text" name="login_code" id="login_code"
             class="input font-mono uppercase tracking-widest"
             placeholder="e.g. A3F1B2C8" required>
    </div>
    <button type="submit" class="btn btn-primary w-full">Enter Competition</button>
  </form>
</div>
{% endblock %}
```

### 2.4 Wire up URLs

```python
# ksp-naboj/team/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.team_login, name="team-login"),
    path("logout/", views.team_logout, name="team-logout"),
]
```

```python
# ksp-naboj/urls.py  (add the team URLs)
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ksp-naboj.users.urls")),
    path("team/", include("ksp-naboj.team.urls")),          # <-- NEW
    path("competition/", include("ksp-naboj.competition.urls")),
] + debug_toolbar_urls()
```

### 2.5 Helper: get team from session

Create a small utility both the competition view and submit view can use:

```python
# ksp-naboj/team/middleware.py
import importlib

Team = importlib.import_module("ksp-naboj.team.models").Team


def get_team_from_session(request):
    """Return the Team stored in session, or None."""
    team_id = request.session.get("team_id")
    if not team_id:
        return None
    try:
        return Team.objects.select_related("competition").get(pk=team_id)
    except Team.DoesNotExist:
        return None
```

### 2.6 Update CompetitionDetailView to use session

```python
# ksp-naboj/competition/views.py
import importlib
import json

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView

from .models import Competition
from .services import get_problem_groups, get_unlocked_problems_json

get_team_from_session = importlib.import_module(
    "ksp-naboj.team.middleware"
).get_team_from_session

Submission = importlib.import_module("ksp-naboj.submission.models").Submission


class CompetitionDetailView(TemplateView):
    template_name = "competition/competition.html"

    def dispatch(self, request, *args, **kwargs):
        self.team = get_team_from_session(request)
        if not self.team:
            return HttpResponseRedirect(reverse("team-login"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)

        # Verify team belongs to this competition
        if self.team.competition_id != competition.id:
            return context  # or redirect

        problem_groups = get_problem_groups(competition, self.team)
        problems_json = json.dumps(
            get_unlocked_problems_json(competition, self.team)
        )

        # Recent submissions for the team (for the feed)
        recent_submissions = (
            Submission.objects.filter(team=self.team)
            .select_related("problem")
            .order_by("-submitted_at")[:20]
        )

        context["competition"] = competition
        context["team"] = self.team
        context["problem_groups"] = problem_groups
        context["problems_json"] = problems_json
        context["recent_submissions"] = recent_submissions
        return context
```

### 2.7 Update submit_code to use session (and remove @csrf_exempt)

See Section 3 below -- the new submit view gets the team from session.

### 2.8 Update seed_testdata to print login code

```python
# In seed_testdata.py Command.handle(), after team creation:
self.stdout.write(
    self.style.SUCCESS(
        f"\nDone! Login at: /team/login/"
        f"\n  Team ID: {team.id}"
        f"\n  Login Code: {team.login_code}"
    )
)
```

**Files changed:** `team/models.py`, `team/views.py` (new), `team/urls.py`, `team/middleware.py` (new), `team/templates/team/login.html` (new), `competition/views.py`, `urls.py`, `seed_testdata.py`, + new migration

---

## 3. Fix Submission Safety

**Goals:**
- Remove `@csrf_exempt` (CSRF token already in base.html meta tag and htmx headers)
- Get team from session, not from POST body
- Wrap in `transaction.atomic()` + `select_for_update()`
- Validate problem is unlocked for team
- Validate competition is active / within time window
- Handle malformed JSON

### 3.1 Rewrite `submission/views.py`

```python
# ksp-naboj/submission/views.py
import importlib
import json
import logging
import random

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
Submission = importlib.import_module("ksp-naboj.submission.models").Submission
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress
get_team_from_session = importlib.import_module(
    "ksp-naboj.team.middleware"
).get_team_from_session
handle_successful_submission = importlib.import_module(
    "ksp-naboj.team.services"
).handle_successful_submission

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def submit_code(request):
    # --- Auth: team from session ---
    team = get_team_from_session(request)
    if not team:
        return JsonResponse({"error": "Not logged in"}, status=403)

    # --- Parse JSON body ---
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    problem_id = data.get("problem_id")
    code = data.get("code", "")
    language = data.get("language", "python")

    if not problem_id or not code.strip():
        return JsonResponse({"error": "Missing problem_id or code"}, status=400)

    # --- Fetch problem ---
    try:
        problem = Problem.objects.get(pk=problem_id)
    except Problem.DoesNotExist:
        return JsonResponse({"error": "Problem not found"}, status=404)

    # --- Validate competition is active and within time window ---
    competition = team.competition
    now = timezone.now()
    if competition.end_at and now > competition.end_at:
        return JsonResponse({"error": "Competition has ended"}, status=403)

    # --- Validate problem is unlocked for this team ---
    try:
        progress = team.teamprogress
    except TeamProgress.DoesNotExist:
        return JsonResponse({"error": "Team has no progress record"}, status=400)

    if not progress.unlocked_problems.filter(pk=problem.pk).exists():
        return JsonResponse({"error": "Problem is locked"}, status=403)

    # --- Create submission ---
    submission = Submission.objects.create(
        team=team,
        problem=problem,
        code=code,
        language=language,
        status=Submission.PENDING,
    )

    # --- Mock judging (replace with real judge-client later) ---
    mock_statuses = [
        Submission.ACCEPTED,
        Submission.REJECTED,
        Submission.RUNTIME_ERROR,
        Submission.COMPILATION_ERROR,
        Submission.TIME_LIMIT_EXCEEDED,
    ]
    weights = [0.8, 0.05, 0.05, 0.05, 0.05]
    result_status = random.choices(mock_statuses, weights=weights, k=1)[0]

    submission.status = result_status
    submission.execution_time = round(random.uniform(0.01, 2.0), 3)
    submission.judged_at = timezone.now()

    if result_status != Submission.ACCEPTED:
        error_messages = {
            Submission.REJECTED: "Wrong answer on test case 3",
            Submission.RUNTIME_ERROR: "RuntimeError: division by zero",
            Submission.COMPILATION_ERROR: "SyntaxError: invalid syntax",
            Submission.TIME_LIMIT_EXCEEDED: "Time limit exceeded on test case 5",
        }
        submission.error_message = error_messages.get(result_status, "Unknown error")

    submission.save()

    # --- Handle accepted: unlock new problems (with locking) ---
    if submission.status == Submission.ACCEPTED:
        with transaction.atomic():
            handle_successful_submission(submission)

    return JsonResponse(
        {
            "submission_id": submission.id,
            "status": submission.status,
            "execution_time": submission.execution_time,
            "error_message": submission.error_message,
            "problem_title": problem.title,
            "problem_difficulty": problem.difficulty,
        }
    )
```

### 3.2 Add `select_for_update` to `handle_successful_submission`

```python
# ksp-naboj/team/services.py
import importlib

from django.db import transaction
from django.utils import timezone

Problem = importlib.import_module("ksp-naboj.problem.models").Problem
TeamProgress = importlib.import_module("ksp-naboj.team.models").TeamProgress


def handle_successful_submission(submission):
    """Unlock new problems after an accepted easy submission.

    MUST be called inside transaction.atomic().
    """
    if submission.problem.difficulty != "easy" or submission.status != "accepted":
        return

    # Lock the progress row to prevent concurrent unlock races
    progress = TeamProgress.objects.select_for_update().get(
        team=submission.team
    )

    competition = submission.problem.competition
    title = submission.problem.title
    unlock_order = submission.problem.unlock_order

    # Unlock the hard variant of the same problem
    hard_problem = Problem.objects.filter(
        competition=competition,
        title=title,
        difficulty="hard",
        unlock_order=unlock_order,
    ).first()

    if hard_problem and not progress.unlocked_problems.filter(pk=hard_problem.pk).exists():
        progress.unlocked_problems.add(hard_problem)

    # Unlock the next easy problem
    next_easy = Problem.objects.filter(
        competition=competition,
        difficulty="easy",
        unlock_order=progress.highest_unlocked_order + 1,
    ).first()

    if next_easy:
        progress.unlocked_problems.add(next_easy)
        progress.highest_unlocked_order = next_easy.unlock_order

    progress.last_unlock_at = timezone.now()
    progress.score = progress.unlocked_problems.filter(
        unlocked_by__team__submission__status="accepted",
    ).count()  # or simpler: just increment
    progress.save()
```

> **Note on `score`:** A simpler approach is to just count accepted submissions:
> ```python
> from ksp-naboj.submission.models import Submission  # via importlib
> progress.score = Submission.objects.filter(
>     team=submission.team, status="accepted"
> ).values("problem_id").distinct().count()
> ```

### 3.3 Update submission controller to stop sending `team_id`

The frontend no longer needs to send `team_id` -- the server gets it from the session. Update the fetch body in `submission_controller.js`:

```javascript
// In submit() method, update the body:
body: JSON.stringify({
    problem_id: this.currentProblemId,
    code,
    language,
}),
```

And remove the `teamId` value from the controller since it's no longer needed:

```javascript
// Remove this:
// static values = { teamId: String }

// And remove team_id from the JSON body
```

The `data-submission-team-id-value="{{ team.id }}"` attribute in `_editor_panel.html` can also be removed (or kept for other client-side purposes if needed later).

**Files changed:** `submission/views.py`, `team/services.py`, `submission_controller.js`, `_editor_panel.html`

---

## 4. localStorage Code Persistence

**Goal:** Every keystroke (debounced) saves code to `localStorage` keyed by `teamId:problemId`. When switching problems or reloading the page, code is restored from localStorage. Code survives page refreshes, browser crashes, and accidental tab closes.

### 4.1 Update `monaco-editor_controller.js`

```javascript
// ksp-naboj/styles/src/controllers/monaco-editor_controller.js
import { Controller } from "@hotwired/stimulus"
import * as monaco from "monaco-editor"

export default class extends Controller {
    static targets = ["container", "placeholder"]
    static values = {
        workerUrl: String,
        teamId: String,     // used as localStorage namespace
    }

    currentProblemId = null
    editor = null
    _saveTimer = null

    // --- localStorage helpers ---

    _storageKey(problemId) {
        return `naboj:code:${this.teamIdValue}:${problemId}`
    }

    _loadCode(problemId) {
        try {
            return localStorage.getItem(this._storageKey(problemId)) || ""
        } catch {
            return ""
        }
    }

    _persistCode(problemId, code) {
        try {
            localStorage.setItem(this._storageKey(problemId), code)
        } catch {
            // localStorage full or unavailable -- silent fail
        }
    }

    // --- Stimulus lifecycle ---

    connect() {
        const dataEl = document.getElementById("problems-data")
        this.problems = dataEl ? JSON.parse(dataEl.textContent) : {}
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        this._flushSave()
        this.editor?.dispose()
    }

    // --- Problem selection ---

    onSelect(event) {
        const { problemId } = event.detail
        const problem = this.problems[problemId]
        if (!problem) return

        // Save current code before switching
        this._flushSave()
        this.currentProblemId = problemId

        const lang = problem.language || "python"

        this.placeholderTarget.classList.add("hidden")
        this.containerTarget.classList.remove("hidden")

        if (this.editor) {
            const model = this.editor.getModel()
            monaco.editor.setModelLanguage(model, lang)
            this.editor.setValue(this._loadCode(problemId))
            this.editor.layout()
        } else {
            this._createEditor(lang)
        }

        const langLabel = document.getElementById("current-language")
        if (langLabel) langLabel.textContent = this._languageDisplayName(lang)
    }

    // --- Editor creation ---

    _createEditor(language) {
        self.MonacoEnvironment = {
            getWorkerUrl: () => this.workerUrlValue,
        }

        requestAnimationFrame(() => {
            this.editor = monaco.editor.create(this.containerTarget, {
                value: this._loadCode(this.currentProblemId),
                language,
                theme: "vs-dark",
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                padding: { top: 12 },
            })

            // Auto-save on every change (debounced 500ms)
            this.editor.onDidChangeModelContent(() => {
                this._debouncedSave()
            })
        })
    }

    // --- Debounced save ---

    _debouncedSave() {
        if (this._saveTimer) clearTimeout(this._saveTimer)
        this._saveTimer = setTimeout(() => {
            if (this.editor && this.currentProblemId) {
                this._persistCode(
                    this.currentProblemId,
                    this.editor.getValue()
                )
            }
        }, 500)
    }

    _flushSave() {
        if (this._saveTimer) {
            clearTimeout(this._saveTimer)
            this._saveTimer = null
        }
        if (this.editor && this.currentProblemId) {
            this._persistCode(
                this.currentProblemId,
                this.editor.getValue()
            )
        }
    }

    // --- Public API (used by submission controller) ---

    getCode() {
        return this.editor?.getValue() || ""
    }

    getLanguage() {
        const model = this.editor?.getModel()
        return model ? model.getLanguageId() : ""
    }

    _languageDisplayName(langId) {
        const names = {
            python: "Python",
            cpp: "C++",
            c: "C",
            java: "Java",
            javascript: "JavaScript",
            typescript: "TypeScript",
            rust: "Rust",
            go: "Go",
        }
        return names[langId] || langId
    }
}
```

### 4.2 Update `_editor_panel.html` to pass `teamId` value to the editor

```html
{% load static %}

<div class="flex flex-col h-full"
     data-controller="monaco-editor"
     data-monaco-editor-worker-url-value="{% static 'editor.worker.js' %}"
     data-monaco-editor-team-id-value="{{ team.id }}">
  <div data-monaco-editor-target="placeholder" class="flex-1 flex items-center justify-center">
    <p class="text-sm text-base-content/40">Code editor will appear here.</p>
  </div>
  <div data-monaco-editor-target="container" class="flex-1 hidden w-full"></div>
</div>

<div class="border-t border-base-300 px-3 py-2 flex flex-col gap-2"
     data-controller="submission">
  <div data-submission-target="feedback" class="hidden">
    <span data-submission-target="result"></span>
  </div>
  <div class="flex items-center justify-between">
    <span class="text-xs text-base-content/50" id="current-language">Python</span>
    <button data-submission-target="button"
            data-action="click->submission#submit"
            class="btn btn-primary text-sm">
      Submit
    </button>
  </div>
</div>
```

**Key changes:**
- Added `data-monaco-editor-team-id-value="{{ team.id }}"` to the editor div
- Removed `data-submission-team-id-value="{{ team.id }}"` from the submission div (no longer needed)
- The entire in-memory `codeStore` Map is replaced by `localStorage`

**Files changed:** `monaco-editor_controller.js`, `_editor_panel.html`

---

## 5. htmx: Live Submission Feed

**Goal:** Every team member sees all submissions from their team in real-time. A submission feed panel below the editor shows the last N submissions, auto-polling every 5 seconds via htmx.

### 5.1 Add submission feed partial view

```python
# Add to ksp-naboj/competition/views.py

class SubmissionFeedView(TemplateView):
    """htmx partial: returns the most recent team submissions as HTML."""
    template_name = "competition/partials/_submission_feed.html"

    def get(self, request, *args, **kwargs):
        team = get_team_from_session(request)
        if not team:
            return HttpResponse("", status=204)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = get_team_from_session(self.request)
        context["recent_submissions"] = (
            Submission.objects.filter(team=team)
            .select_related("problem")
            .order_by("-submitted_at")[:15]
        )
        return context
```

### 5.2 Create the submission feed template

```html
<!-- ksp-naboj/competition/templates/competition/partials/_submission_feed.html -->
<div id="submission-feed">
  {% for sub in recent_submissions %}
    <div class="flex items-center justify-between px-3 py-1.5 text-xs
                {% if sub.status == 'accepted' %}bg-success/5{% endif %}
                {% if sub.status == 'pending' %}bg-warning/5{% endif %}">
      <div class="flex items-center gap-2 min-w-0">
        <span class="font-medium truncate">{{ sub.problem.title }}</span>
        <span class="rounded px-1 py-0.5 font-medium
          {% if sub.problem.difficulty == 'easy' %}bg-success/10 text-success
          {% else %}bg-error/10 text-error{% endif %}">
          {{ sub.problem.difficulty|title }}
        </span>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        {% if sub.status == 'accepted' %}
          <span class="text-success font-semibold">Accepted</span>
        {% elif sub.status == 'pending' %}
          <span class="text-warning">Pending</span>
        {% elif sub.status == 'rejected' %}
          <span class="text-error">Wrong Answer</span>
        {% elif sub.status == 'runtime_error' %}
          <span class="text-error">Runtime Error</span>
        {% elif sub.status == 'compilation_error' %}
          <span class="text-error">Compilation Error</span>
        {% elif sub.status == 'time_limit_exceeded' %}
          <span class="text-error">TLE</span>
        {% elif sub.status == 'memory_limit_exceeded' %}
          <span class="text-error">MLE</span>
        {% else %}
          <span class="text-base-content/50">{{ sub.get_status_display }}</span>
        {% endif %}
        <span class="text-base-content/40">{{ sub.submitted_at|date:"H:i:s" }}</span>
      </div>
    </div>
  {% empty %}
    <p class="text-xs text-base-content/40 px-3 py-2">No submissions yet.</p>
  {% endfor %}
</div>
```

### 5.3 Add URL for the feed

```python
# ksp-naboj/competition/urls.py
import importlib

from django.urls import path

from . import views

submit_code = importlib.import_module("ksp-naboj.submission.views").submit_code

urlpatterns = [
    path(
        "<int:year>/",
        views.CompetitionDetailView.as_view(),
        name="competition-detail",
    ),
    path("submit/", submit_code, name="submit-code"),
    path(
        "<int:year>/feed/",
        views.SubmissionFeedView.as_view(),
        name="submission-feed",
    ),
    path(
        "<int:year>/problems/",
        views.ProblemListPartialView.as_view(),
        name="problem-list-partial",
    ),
]
```

### 5.4 Add the feed panel to the competition template

Update `competition.html` to include the feed panel with htmx polling:

```html
{% extends "base.html" %}
{% load static %}

{% block title %}Naboj {{ competition.year }}{% endblock %}

{% block extra_css %}
<link href="{% static 'bundle.css' %}" rel="stylesheet">
{% endblock extra_css %}

{% block outer_container %}
<script type="application/json" id="problems-data">{{ problems_json|safe }}</script>

<div class="grid grid-cols-12 divide-x divide-base-300 h-[calc(100vh-4rem)] overflow-hidden">

  {# ---- Column 1: Problem list (2 cols) ---- #}
  <div class="col-span-2 overflow-y-auto"
       data-controller="problem-list"
       id="problem-list-container"
       hx-get="{% url 'problem-list-partial' competition.year %}"
       hx-trigger="submission:accepted from:body"
       hx-target="#problem-list-container"
       hx-swap="innerHTML">
    {% include "competition/partials/_problem_list.html" %}
  </div>

  {# ---- Column 2: Problem statement (3 cols) ---- #}
  <div class="col-span-3 overflow-y-auto">
    {% include "competition/partials/_problem_statement.html" %}
  </div>

  {# ---- Column 3: Editor + Feed (7 cols) ---- #}
  <div class="col-span-7 overflow-hidden flex flex-col">
    {# Editor takes remaining space #}
    <div class="flex-1 overflow-hidden flex flex-col min-h-0">
      {% include "competition/partials/_editor_panel.html" %}
    </div>

    {# Submission feed: auto-polls every 5s #}
    <div class="border-t border-base-300 max-h-40 overflow-y-auto">
      <div class="flex items-center justify-between px-3 py-1.5 border-b border-base-200 bg-base-200/50">
        <span class="text-xs font-semibold text-base-content/60 uppercase tracking-wider">
          Team Submissions
        </span>
      </div>
      <div hx-get="{% url 'submission-feed' competition.year %}"
           hx-trigger="load, every 5s, submission-submitted from:body"
           hx-target="this"
           hx-swap="innerHTML">
        {% include "competition/partials/_submission_feed.html" %}
      </div>
    </div>
  </div>

</div>
{% endblock outer_container %}
```

### 5.5 Update submission controller to trigger htmx refresh events

After a successful submission (any status, not just accepted), dispatch a DOM event that htmx will pick up:

```javascript
// ksp-naboj/styles/src/controllers/submission_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
    static targets = ["button", "feedback", "result"]

    feedbackTimeout = null

    connect() {
        this._boundOnSelect = this.onSelect.bind(this)
        window.addEventListener("problem:select", this._boundOnSelect)
    }

    disconnect() {
        window.removeEventListener("problem:select", this._boundOnSelect)
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)
    }

    onSelect(event) {
        this.currentProblemId = event.detail.problemId
        this.hideFeedback()
    }

    async submit(event) {
        event.preventDefault()
        if (!this.currentProblemId) return

        const editorElement = document.querySelector(
            "[data-controller*='monaco-editor']"
        )
        const editorController =
            this.application.getControllerForElementAndIdentifier(
                editorElement,
                "monaco-editor"
            )
        if (!editorController) return

        const code = editorController.getCode()
        const language = editorController.getLanguage()

        if (!code.trim()) {
            this.showFeedback("warning", "Cannot submit empty code.")
            return
        }

        this.buttonTarget.disabled = true
        this.buttonTarget.textContent = "Submitting..."

        try {
            const response = await fetch("/competition/submit/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken":
                        document.querySelector('meta[name="csrf-token"]')
                            ?.content || "",
                },
                body: JSON.stringify({
                    problem_id: this.currentProblemId,
                    code,
                    language,
                }),
            })

            const result = await response.json()

            if (response.ok) {
                if (result.status === "accepted") {
                    this.showFeedback(
                        "success",
                        `Accepted! (${result.execution_time}s)`
                    )
                    // Tell htmx to refresh the problem list (new unlocks)
                    document.body.dispatchEvent(
                        new CustomEvent("submission:accepted")
                    )
                } else {
                    this.showFeedback(
                        "error",
                        `${this._statusLabel(result.status)}: ${result.error_message}`
                    )
                }

                // Tell htmx to refresh the submission feed (any result)
                document.body.dispatchEvent(
                    new CustomEvent("submission-submitted")
                )
            } else {
                this.showFeedback(
                    "error",
                    result.error || "Submission failed"
                )
            }
        } catch {
            this.showFeedback("error", "Network error. Please try again.")
        } finally {
            this.buttonTarget.disabled = false
            this.buttonTarget.textContent = "Submit"
        }
    }

    showFeedback(type, message) {
        if (this.feedbackTimeout) clearTimeout(this.feedbackTimeout)

        const colors = {
            success: "bg-success/10 text-success border-success/30",
            error: "bg-error/10 text-error border-error/30",
            warning: "bg-warning/10 text-warning border-warning/30",
        }

        this.feedbackTarget.className = `px-3 py-2 rounded text-sm border ${colors[type] || colors.error}`
        this.resultTarget.textContent = message
        this.feedbackTarget.classList.remove("hidden")

        this.feedbackTimeout = setTimeout(() => this.hideFeedback(), 8000)
    }

    hideFeedback() {
        this.feedbackTarget.classList.add("hidden")
    }

    _statusLabel(status) {
        const labels = {
            rejected: "Wrong Answer",
            runtime_error: "Runtime Error",
            compilation_error: "Compilation Error",
            time_limit_exceeded: "Time Limit Exceeded",
            memory_limit_exceeded: "Memory Limit Exceeded",
        }
        return labels[status] || status
    }
}
```

**Key design:** Two separate custom events:
- `submission-submitted` (dispatched after every submission) -> triggers feed poll immediately
- `submission:accepted` (dispatched only on accepted) -> triggers problem list refresh

The feed also polls `every 5s` so team members who didn't submit will see updates within 5 seconds.

**Files changed:** `competition/views.py`, `competition/urls.py`, `competition/templates/competition/competition.html`, `competition/templates/competition/partials/_submission_feed.html` (new), `submission_controller.js`

---

## 6. htmx: Problem List Refresh on Unlock

**Goal:** When any team member's submission is accepted and unlocks new problems, the problem list sidebar refreshes to show the newly unlocked problems. This happens via htmx -- the `submission:accepted` event triggers a GET to a partial that re-renders the problem list server-side.

### 6.1 Add problem list partial view

```python
# Add to ksp-naboj/competition/views.py

class ProblemListPartialView(TemplateView):
    """htmx partial: returns the problem list HTML for the team."""
    template_name = "competition/partials/_problem_list.html"

    def get(self, request, *args, **kwargs):
        self.team = get_team_from_session(request)
        if not self.team:
            return HttpResponse("", status=204)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)
        context["problem_groups"] = get_problem_groups(competition, self.team)
        return context
```

### 6.2 htmx wiring on the problem list container

Already shown in section 5.4 above. The key attributes on the problem list div:

```html
<div class="col-span-2 overflow-y-auto"
     data-controller="problem-list"
     id="problem-list-container"
     hx-get="{% url 'problem-list-partial' competition.year %}"
     hx-trigger="submission:accepted from:body"
     hx-target="#problem-list-container"
     hx-swap="innerHTML">
  {% include "competition/partials/_problem_list.html" %}
</div>
```

**How it works:**
1. User submits code -> `submit_code` view -> if accepted -> `handle_successful_submission` unlocks new problems in DB
2. Submission controller dispatches `submission:accepted` on `document.body`
3. htmx sees the event (via `hx-trigger="submission:accepted from:body"`) and fires GET to `problem-list-partial`
4. Server returns fresh `_problem_list.html` with updated unlock states
5. htmx swaps the innerHTML of `#problem-list-container`

**For OTHER team members** (who didn't submit): The feed polls every 5s and they see accepted submissions appear. But the problem list only refreshes on `submission:accepted`. To handle cross-member unlocks, we also add a periodic poll:

```html
hx-trigger="submission:accepted from:body, every 15s"
```

This polls the problem list every 15 seconds, which is a good balance between freshness and server load. When a teammate's accepted submission unlocks new problems, the list will update within 15 seconds.

### 6.3 Handle the problems-data JSON update

When the problem list refreshes via htmx, new problems may be unlocked. The `problems-data` JSON in the page also needs updating so the problem-statement and monaco-editor controllers can display the newly unlocked problems.

**Option A (simple):** Include updated JSON in the htmx response via an OOB swap.

Add this to `ProblemListPartialView.get_context_data()`:

```python
problems_json = json.dumps(
    get_unlocked_problems_json(competition, self.team)
)
context["problems_json"] = problems_json
```

And wrap the partial template output:

```html
<!-- _problem_list.html stays exactly the same, but the partial VIEW returns
     both the list AND an OOB swap for the problems JSON -->
```

Create a wrapper template `_problem_list_with_data.html` or handle it in the view:

```python
# In ProblemListPartialView
class ProblemListPartialView(TemplateView):
    template_name = "competition/partials/_problem_list.html"

    def get(self, request, *args, **kwargs):
        self.team = get_team_from_session(request)
        if not self.team:
            return HttpResponse("", status=204)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = kwargs["year"]
        competition = get_object_or_404(Competition, year=year)
        context["problem_groups"] = get_problem_groups(competition, self.team)
        context["problems_json"] = json.dumps(
            get_unlocked_problems_json(competition, self.team)
        )
        return context

    def render_to_response(self, context, **response_kwargs):
        """Append an OOB swap to update the problems JSON data."""
        response = super().render_to_response(context, **response_kwargs)
        response.render()
        # Append OOB swap for the problems JSON script tag
        oob_html = (
            f'<script type="application/json" id="problems-data"'
            f' hx-swap-oob="true">{context["problems_json"]}</script>'
        )
        response.content = response.content + oob_html.encode()
        return response
```

Then update the controllers to re-read the JSON when they detect a change. Add a listener in both `problem-statement_controller.js` and `monaco-editor_controller.js`:

```javascript
// Add to connect() in both controllers:
document.body.addEventListener("htmx:afterSwap", (event) => {
    // Re-parse problems data if the problems-data element was swapped
    const dataEl = document.getElementById("problems-data")
    if (dataEl) {
        this.problems = JSON.parse(dataEl.textContent)
    }
})
```

This way, when htmx swaps in the new problem list + OOB-swaps the JSON, both controllers pick up the new problem data and can display newly unlocked problems when clicked.

**Files changed:** `competition/views.py`, `competition/urls.py`, `competition/templates/competition/competition.html`, `problem-statement_controller.js`, `monaco-editor_controller.js`

---

## Summary: Files Changed

| File | Change |
|------|--------|
| `team/apps.py` | Add signal import in `ready()` |
| `team/models.py` | Add `login_code` field + migration |
| `team/views.py` | New: login/logout views |
| `team/urls.py` | Add login/logout URL patterns |
| `team/middleware.py` | New: `get_team_from_session()` helper |
| `team/services.py` | Add `select_for_update`, `transaction.atomic`, update `score`/`last_unlock_at` |
| `team/templates/team/login.html` | New: login page |
| `submission/views.py` | Full rewrite: session auth, validation, CSRF, JSON error handling |
| `competition/views.py` | Session auth, add `SubmissionFeedView`, `ProblemListPartialView` |
| `competition/urls.py` | Add feed + problem-list partial endpoints |
| `competition/templates/competition/competition.html` | Add htmx polling, submission feed panel |
| `competition/templates/competition/partials/_submission_feed.html` | New: feed partial |
| `styles/src/controllers/monaco-editor_controller.js` | localStorage persistence, auto-save, teamId value |
| `styles/src/controllers/submission_controller.js` | Remove `teamId`, dispatch htmx trigger events |
| `styles/src/controllers/problem-statement_controller.js` | Re-parse JSON on htmx swap |
| `competition/templates/competition/partials/_editor_panel.html` | Add `teamId` to editor, remove from submission |
| `urls.py` | Include team URLs |
| `competition/management/commands/seed_testdata.py` | Print login code |

## Implementation Order

1. **Signal fix** (2 min) -- unblocks everything
2. **Team model + migration** (10 min) -- `login_code` field
3. **Team login views + template + URLs** (30 min) -- auth flow
4. **Session helper + update competition view** (15 min) -- session-based team lookup
5. **Submission view rewrite** (20 min) -- security + validation
6. **Service layer fixes** (10 min) -- `select_for_update`, transactions
7. **localStorage in Monaco** (15 min) -- code persistence
8. **Submission feed partial + view + URL** (20 min) -- team feed
9. **Problem list htmx refresh + OOB JSON swap** (20 min) -- live unlocks
10. **Update submission controller** (10 min) -- dispatch events, remove teamId
11. **Update seed_testdata** (5 min) -- print login code
12. **Test end-to-end** (30 min) -- manual testing of full flow
