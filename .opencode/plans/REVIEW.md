# Deep Review: KSP-Naboj-Web Implementation

> **Review Date:** 2026-05-30
> **Scope:** Full codebase review covering backend, frontend, architecture, and alignment with the Naboj competition format.
> **Reference:** `.opencode/plans/FRONTEND-PLAN.md` (Parts 1-8), `CLAUDE.md`, naboj.org rules, Trojsten conventions.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Competition Format Alignment](#2-competition-format-alignment)
3. [Backend Review](#3-backend-review)
4. [Frontend Plan Review (Part by Part)](#4-frontend-plan-review)
5. [Django Best Practices Audit](#5-django-best-practices-audit)
6. [Security Review](#6-security-review)
7. [Architecture & Code Quality](#7-architecture--code-quality)
8. [Prioritized Action Items](#8-prioritized-action-items)

---

## 1. Executive Summary

The project is a well-structured early-stage Django application that adapts the Naboj math competition format to programming. Parts 1-5 of the FRONTEND-PLAN are marked as complete, Part 6 is partially done (model fields added, timer controller not yet built), and Parts 7-8 are still pending.

**What's working well:**
- Clean service-layer separation for business logic
- Solid progressive-unlock mechanism with comprehensive tests (312 lines)
- Good Stimulus controller architecture with event-based decoupling
- Proper OIDC integration for Trojsten ID
- Docker-ready with multi-stage builds

**Critical issues found:**
- Signals are never registered (empty `ready()` in team/apps.py)
- `@csrf_exempt` on the submission endpoint
- Team name uniqueness is global instead of per-competition
- No authorization checks on any view
- XSS risk from unsanitized markdown rendering

---

## 2. Competition Format Alignment

### How Naboj Math Works (from naboj.org)
- Teams of 4-5 students, 120-minute competition
- Start with 6 problems, solve one to unlock the next
- Answers are single numerical values (instant verification)
- **Blocking penalty** on incorrect answers: n-th wrong answer blocks the problem for n minutes
- Tiebreaker: highest problem ordinal numbers solved, then submission time
- Junior and Senior categories

### How This Project Adapts It

| Naboj Math Rule | Current Implementation | Assessment |
|---|---|---|
| 6 initial problems | First 6 easy problems unlocked via signal | Correct |
| Solve to unlock next | `handle_successful_submission` unlocks next easy + corresponding hard | Correct, but **only easy submissions trigger unlocks** which is a deliberate design choice |
| Blocking penalty on wrong answer | Not implemented | **Missing** - important for preventing brute-force |
| Tiebreaker by problem difficulty | `score` field exists but never incremented; no tiebreaker logic | **Missing** |
| 120-minute timer | `start_at`/`end_at` fields exist; timer controller not built | **Partially done** |
| Competition end enforcement | No check that submissions are within time window | **Missing** |
| Team member tracking | `members` is a plain CharField (comma-separated string) | **Weak** - no link to User model |

### Key Gaps vs. Naboj Format
1. **No submission blocking/cooldown** - In real Naboj, wrong answers block the problem for increasing durations. This is a core mechanic that prevents guessing.
2. **No time-window enforcement** - Nothing stops submissions after `end_at`.
3. **No score calculation** - `TeamProgress.score` exists but is never updated.
4. **No scoreboard** - No view for rankings or tiebreaker logic.

---

## 3. Backend Review

### 3.1 Models

**Competition** (`competition/models.py`)
- Minimal and appropriate for current scope.
- `start_at`/`end_at` are nullable - good for draft competitions but should be validated before activation.

**Problem** (`problem/models.py`)
- Good: `unique_together = ("competition", "title", "difficulty")` prevents duplicate pairs.
- Good: `judge_task` is globally unique.
- Consider: `unlock_order` should have a unique constraint per `(competition, difficulty, unlock_order)` to prevent ordering conflicts.

**Team** (`team/models.py`)
- **Issue:** `name = CharField(unique=True)` is globally unique. A team called "Alpha" in 2025 blocks "Alpha" in 2026. Should be `unique_together = ("name", "competition")`.
- **Issue:** `members = CharField(max_length=500)` stores members as a comma-separated string. This means:
  - No link between User accounts and team membership
  - Can't enforce "only team members can submit"
  - Can't track "which user is working on which problem" (a listed future feature)
- **Recommendation:** Create a `TeamMembership` model with FK to both `Team` and `User`, or at minimum add an M2M `members` field to User.

**TeamProgress** (`team/models.py`)
- Good: OneToOne with Team is correct.
- Good: `highest_unlocked_order` avoids re-scanning all unlocked problems.
- **Issue:** `score` field is never updated anywhere in the codebase.
- **Missing:** No `last_unlock_at` update in `handle_successful_submission`.

**Submission** (`submission/models.py`)
- Good: Comprehensive status choices covering all judge outcomes.
- Good: Tracks both `submitted_at` and `judged_at`.
- Consider: Add a `team_member` or `submitted_by` FK to User for per-user tracking.

### 3.2 Services

**`team/services.py` - `handle_successful_submission()`**
- Core unlock logic is correct and well-tested.
- **Issue:** Only processes easy submissions. If the design intent is that hard-problem solutions also contribute to score/ranking, this needs updating.
- **Issue:** No `select_for_update()` - concurrent accepted submissions could cause race conditions (two unlocks of the same problem, or skipping an unlock_order).
- **Issue:** Doesn't update `TeamProgress.score` or `last_unlock_at`.
- **Issue:** No transaction wrapping - partial failures could leave inconsistent state.

**`competition/services.py` - `get_problem_groups()`**
- Good: Uses `values_list("id", flat=True)` for efficient ID lookups.
- Good: Single query for problems, single query for unlocked IDs, single query for solved IDs.
- **Optimization opportunity:** Could combine unlocked + solved into a single annotated query.
- **Issue:** Filters by `unlock_order__lte=max_order` which shows all problems up to the highest unlocked order, even ones that aren't actually unlocked (e.g., hard variants that weren't earned). This is intentional for the UI (showing locked items) but the naming could be clearer.

**`competition/services.py` - `get_unlocked_problems_json()`**
- Good: Only returns unlocked problems (safe for client-side use).
- Good: `select_related("competition")` avoids N+1.
- **Issue:** Returns full `description` for all unlocked problems at once. For large competitions this could be a lot of data in the initial page load. Consider lazy-loading descriptions.

### 3.3 Signals

**`team/signals.py`**

**CRITICAL BUG:** The signals are defined but never imported. `team/apps.py` has:
```python
def ready(self):
    pass
```
This means `create_team_progress` and `unlock_problem_for_teams` are **never registered** with Django's signal dispatcher. Creating a Team will NOT auto-create TeamProgress, and new problems will NOT auto-unlock for existing teams.

**Why the tests pass anyway:** The test files themselves `import` from `signals.py` or `services.py`, which triggers the signal registration as a side effect during the test run. But in production with `manage.py runserver` or gunicorn, if nothing else imports `signals.py`, the signals won't fire.

**Fix:**
```python
def ready(self):
    from . import signals  # noqa: F401
```

**Additional signal issues:**
- `unlock_problem_for_teams` calls `progress.save()` inside a loop over all teams - should use `bulk_update` or at least wrap in a transaction.
- Magic number `6` for initial unlock count is hardcoded in both the signal and the seeder. Should be a constant or competition-level setting.

### 3.4 Views

**`CompetitionDetailView`**
- Good: Uses `get_object_or_404` for both competition and team.
- **Issue:** No authentication required. Any anonymous user can view any team's data by guessing the `team_id` query parameter.
- **Issue:** No check that the requesting user belongs to the team.
- **Issue:** Uses `self.request.GET.get("team_id")` - this is fine for development but needs to be replaced with proper user-team resolution before production.

**`submit_code`**
- **Issue:** `@csrf_exempt` - see Security section.
- **Issue:** No authentication check.
- **Issue:** No check that the team belongs to the competition or that the problem is actually unlocked for the team.
- **Issue:** `json.loads(request.body)` with no error handling - malformed JSON will cause a 500.
- **Issue:** No rate limiting.
- **Good:** The mock judging with weighted probabilities is a reasonable placeholder.

### 3.5 Tests

**`team/tests.py` (119 lines)** - Good coverage of model basics.

**`team/tests_services.py` (312 lines)** - Excellent coverage of the progressive unlock mechanism. Tests cover:
- Initial unlock of 6 problems
- Hard problem unlock on easy solve
- Next easy unlock on easy solve
- Only easy submissions trigger unlocks
- Only accepted submissions trigger unlocks
- Multiple sequential unlocks
- Edge cases (no next problem, no hard version, already unlocked)
- Independent team progress
- `highest_unlocked_order` tracking

**Missing test coverage:**
- `competition/services.py` - no tests for `get_problem_groups` or `get_unlocked_problems_json`
- `submission/views.py` - no tests for the submit endpoint
- `competition/views.py` - no tests for the competition detail view
- `run_tests.py` references `competition.tests`, `problem.tests`, `submission.tests` which are empty or don't exist

---

## 4. Frontend Plan Review

### Part 1: Foundation (Views, URLs, Base Template) - COMPLETE

**Assessment: Good**
- Grid layout (2-3-7 columns) is implemented correctly.
- `h-[calc(100vh-4rem)]` assumes a 4rem navbar, which matches the current navbar height.
- Template extends `base.html` and overrides `outer_container` block correctly.
- `django-htmx` middleware is properly added to settings.

**Minor concern:** The 12-column split (2-3-7) gives the problem list only ~16% of viewport width. On a 1920px screen that's about 307px, which is tight for problem titles. On a 1366px laptop that's about 220px.

### Part 2: Problem List Sidebar - COMPLETE

**Assessment: Good with minor issues**
- `get_problem_groups()` service method is clean and efficient.
- Template properly renders grouped problems with easy/hard sub-rows.
- Visual states (unlocked/solved/locked) are implemented with icons and color coding.
- Stimulus controller dispatches `problem:select` events correctly.

**Issues:**
- The `problem-list_controller.js` declares `static targets = ["item"]` but never uses the `item` target. This is dead code.
- Highlight class `bg-primary/10` is hardcoded in JS - should use Stimulus CSS classes for consistency.
- No keyboard navigation support (can't tab through problems).

### Part 3: Problem Statement Panel - COMPLETE

**Assessment: Good with XSS concern**
- `marked.js` renders markdown client-side, which is fine for performance.
- Controller properly listens for `problem:select` events.
- Badge styling for Easy/Hard is clear.

**Issues:**
- `this.descriptionTarget.innerHTML = marked.parse(problem.description)` - this is an XSS vector. If problem descriptions contain malicious HTML/JS, they'll execute. In practice this is low risk since problem descriptions come from admin-created content, but it's still bad practice.
- **Recommendation:** Use `DOMPurify` to sanitize the HTML output from `marked.parse()`, or render markdown server-side.
- Multiple controllers (`problem-statement` and `monaco-editor`) independently parse the same `#problems-data` JSON. This is fine for now but could be a shared concern.

### Part 4: Monaco Editor Integration - COMPLETE

**Assessment: Good, well-implemented**
- Worker URL configuration via Stimulus value is clean.
- `requestAnimationFrame` for editor creation prevents layout thrashing.
- Per-problem code storage via `Map()` is correct.
- Editor options (no minimap, dark theme, auto layout) are sensible defaults.
- Language switching based on problem restrictions works.
- `ResizeObserver` not used, but `automaticLayout: true` handles it.

**Issues:**
- Code is stored only in memory (`this.codeStore`). Page reload loses all work. The plan mentions "Code preservation" in Part 8, but `localStorage` persistence should be a higher priority.
- `self.MonacoEnvironment` is set inside `_createEditor()` which is called on first problem selection. If somehow called twice, the global is just overwritten (harmless but sloppy).
- No error handling if Monaco fails to load (e.g., worker URL is wrong).

### Part 5: Submission Flow (Mock) - COMPLETE

**Assessment: Functional but has coupling issues**

The submission controller works end-to-end: click Submit -> POST code -> show result.

**Issues:**
- **Tight coupling:** The submission controller directly queries the DOM for the editor controller:
  ```javascript
  const editorElement = document.querySelector("[data-controller*='monaco-editor']")
  const editorController = this.application.getControllerForElementAndIdentifier(editorElement, "monaco-editor")
  ```
  This breaks the Stimulus pattern of controller independence. Better approach: use a shared Stimulus outlet or event-based data passing.
- **CSRF handling is fragile:** Falls back from `meta[name="csrf-token"]` to `[name="csrfmiddlewaretoken"]`, but currently `@csrf_exempt` makes this moot. When CSRF is properly enabled, this needs testing.
- Submission URL `/competition/submit/` is hardcoded in JS. Should use Django's `{% url %}` tag to generate the URL and pass it as a Stimulus value.
- After an accepted submission, `submission:accepted` event is dispatched but nothing listens for it yet (Part 7 work).
- The `team_id` is passed as a Stimulus value from the template, which means it's in the HTML. Combined with `@csrf_exempt` and no auth, anyone can submit as any team.

### Part 6: Competition Timer - PARTIALLY COMPLETE

**Assessment: Model fields added, controller and UI not built**

- `start_at` and `end_at` fields added to Competition model. Migration exists.
- Timer Stimulus controller (`timer_controller.js`) is **not yet created**.
- Timer bar in the competition template is **not yet added**.
- No server-side enforcement of competition time window.

**Recommendation for implementation:**
- Timer should use `setInterval` with 1-second ticks, comparing against `end_at`.
- Consider server-time sync (pass server time in template context) to avoid client clock skew.
- When timer reaches zero, disable the submit button and show "Competition ended" message.
- Server-side: `submit_code` should reject submissions where `now() > competition.end_at`.

### Part 7: Dynamic Updates with htmx - NOT STARTED

**Assessment: Well-planned, critical for UX**

The plan outlines:
- Problem list polling after submissions (htmx partial endpoint)
- Submission status polling (for real judge integration)
- Score updates via htmx oob-swap
- Future WebSocket/SSE for team coordination

**Recommendations:**
- htmx polling every 10s for the problem list is reasonable but consider using `hx-trigger="submission:accepted from:body"` for immediate refresh after accepted submissions.
- For the submission status polling, `hx-trigger="every 2s[!data-resolved]"` pattern works well - stop polling once the submission reaches a terminal state.
- The problem list partial endpoint should reuse `get_problem_groups()` from services - good that the service layer already exists for this.

### Part 8: Polish and Edge Cases - NOT STARTED

**Key items from the plan:**
- Responsive behavior (tabs on narrow screens)
- Empty states
- Loading states
- Error handling
- Dark mode consistency
- Accessibility
- Code preservation (localStorage)

**Priority recommendation:**
1. Code preservation (localStorage) - users will lose work on page reload
2. Error handling - Monaco load failures, network errors
3. Empty states - competition not started, no team
4. Responsive behavior

---

## 5. Django Best Practices Audit

### 5.1 Project Structure

| Practice | Status | Notes |
|---|---|---|
| Apps inside project package | Yes | Apps at `ksp-naboj/{app}/` level |
| Explicit AppConfig with labels | Yes | Labels use underscores (`ksp_naboj_team`) |
| Service layer for business logic | Yes | `services.py` in competition and team apps |
| Fat models, thin views | Partial | Models are actually quite thin; business logic is properly in services but not on models |
| Custom managers/querysets | No | No custom managers used anywhere |
| Proper signal registration | **No** | `ready()` is empty |

### 5.2 Settings

| Practice | Status | Notes |
|---|---|---|
| Environment-based config | Yes | Using `environs` |
| Secret key from env | Yes | `env("SECRET_KEY")` |
| Debug from env | Yes | `env.bool("DEBUG", default=False)` |
| Database URL from env | Yes | `env.dj_db_url("DATABASE_URL")` |
| Split settings (base/dev/prod) | No | Single `settings.py` - acceptable for small projects |
| HSTS headers | Yes | `SECURE_HSTS_SECONDS = 3600` |

**Note on HSTS:** `SECURE_HSTS_SECONDS = 3600` is set unconditionally, including in development. If running dev over HTTP, this could cause browser issues. Consider making it conditional on `not DEBUG`.

### 5.3 URL Patterns

| Practice | Status | Notes |
|---|---|---|
| Named URL patterns | Partial | `competition-detail` and `submit-code` are named, but not all URLs |
| App-level URL namespaces | No | No `app_name` in any app's `urls.py` |
| REST-style URLs | Partial | `<int:year>/` is good, but `submit/` under competition is not ideal (should be under submission or use `/competition/<year>/submit/`) |

**Recommendation:** Add `app_name` to each app's `urls.py` for proper namespacing:
```python
app_name = "competition"
```

### 5.4 Templates

| Practice | Status | Notes |
|---|---|---|
| Template inheritance | Yes | `base.html` -> `competition.html` |
| Partial templates with `_` prefix | Yes | `_problem_list.html`, etc. |
| Template tags for reusable rendering | Yes | Custom `forms` and `version` tags |
| Context processors | Minimal | Only Django defaults |

### 5.5 Admin

| Practice | Status | Notes |
|---|---|---|
| All models registered | Yes | All models have admin classes |
| list_display configured | Yes | All admins have meaningful displays |
| list_filter and search_fields | Yes | Appropriate filters on all models |
| Read-only fields where appropriate | Partial | `submitted_at` is read-only in SubmissionAdmin, but `created_at` fields elsewhere are not |

### 5.6 Database & Queries

| Practice | Status | Notes |
|---|---|---|
| select_related / prefetch_related | Partial | Used in `get_unlocked_problems_json` but missing in views and signals |
| Avoiding N+1 queries | Partial | `get_problem_groups` makes 3 queries (good), but `unlock_problem_for_teams` signal has N+1 in its loop |
| Using F() and Q() objects | No | Not needed yet but would help with atomic updates |
| Database transactions | No | `handle_successful_submission` should be wrapped in `transaction.atomic()` |
| Index optimization | No | No custom indexes defined; `unlock_order` queries would benefit from an index |

### 5.7 Testing

| Practice | Status | Notes |
|---|---|---|
| Test naming conventions | Yes | Descriptive test method names |
| setUp/tearDown usage | Yes | Proper test setup |
| Factory pattern | No | Tests create objects directly - consider `factory_boy` or at least helper methods |
| Coverage of business logic | Good | 312 lines for unlock logic |
| Coverage of views | None | No view tests |
| Coverage of edge cases | Good | Unlock tests cover many edge cases |

### 5.8 Imports

| Practice | Status | Notes |
|---|---|---|
| Standard imports | **Problematic** | `importlib.import_module()` used extensively |

The hyphenated project name (`ksp-naboj`) prevents normal Python imports like `from ksp_naboj.problem.models import Problem`. Instead, the codebase uses:
```python
Problem = importlib.import_module("ksp-naboj.problem.models").Problem
```

This is a significant code smell. It:
- Breaks IDE autocompletion and type checking
- Makes refactoring harder
- Is unusual and confusing for new contributors
- Circumvents Python's import system

**Root cause:** The project directory is named `ksp-naboj` with a hyphen, which is not a valid Python identifier. Django can handle this with explicit `name` in AppConfig, but cross-app imports become painful.

**Recommendation:** Either rename the project directory to `ksp_naboj` (preferred) or create a package alias. This is a foundational issue that affects the entire codebase.

---

## 6. Security Review

### 6.1 Critical Issues

**`@csrf_exempt` on `submit_code`**
- **Risk:** High. Any website can craft a form that submits code as any team.
- **Impact:** Cheating, score manipulation, potentially malicious code injection into the judge.
- **Fix:** Remove `@csrf_exempt`. The frontend already attempts to send CSRF tokens. Once `@csrf_exempt` is removed, ensure the CSRF token is properly included in fetch requests (it's already in the meta tag via `base.html`).

**No Authentication on Views**
- **Risk:** High. Anyone can view competition data and submit as any team.
- **Fix:** Add `LoginRequiredMixin` to `CompetitionDetailView` and `@login_required` to `submit_code`. Additionally verify the user is a member of the team they're submitting for.

**Team ID in Query Parameter**
- **Risk:** Medium. Even after auth is added, if `team_id` comes from a query param, users could submit for other teams.
- **Fix:** Derive the team from the authenticated user's team membership, not from a query parameter.

### 6.2 XSS Concerns

**Markdown Rendering**
- `marked.parse()` output is assigned to `innerHTML` without sanitization.
- Problem descriptions are admin-created, so risk is low, but defense-in-depth says sanitize anyway.
- **Fix:** Add `DOMPurify`: `this.descriptionTarget.innerHTML = DOMPurify.sanitize(marked.parse(...))`

**`{{ problems_json|safe }}`**
- The `|safe` filter prevents Django from escaping the JSON. If any problem data contains `</script>`, it could break out of the script tag.
- **Fix:** Use `{{ problems_json|json_script:"problems-data" }}` instead of manually writing the script tag. Django's `json_script` filter handles escaping correctly.

### 6.3 Input Validation

- `submit_code` does `json.loads(request.body)` with no try/except. Malformed JSON causes a 500 error.
- No validation that `language` is a supported language.
- No validation that the problem is unlocked for the team before accepting a submission.
- No validation that the competition is currently active.

---

## 7. Architecture & Code Quality

### 7.1 Strengths

1. **Clean separation of concerns** - Models define data, services contain business logic, views handle HTTP, signals handle side effects. This is textbook Django architecture.

2. **Event-driven frontend** - The Stimulus controllers communicate via custom DOM events (`problem:select`, `submission:accepted`). This keeps controllers decoupled and testable.

3. **Progressive unlock logic** - Well-designed: solving an easy problem unlocks its hard variant AND the next easy problem. This prevents "wasted unlocks" where solving a hard problem could block progression.

4. **Test quality** - The 312-line test suite for the unlock mechanism is thorough, covering happy paths, edge cases, and cross-team isolation.

5. **Docker setup** - Multi-stage build with separate CSS/JS build stage is efficient. The compose setup with hot-reload is developer-friendly.

### 7.2 Concerns

1. **`importlib` everywhere** - As discussed, this is a workaround for the hyphenated package name. It's the single biggest code quality issue.

2. **No transactions** - `handle_successful_submission` modifies multiple related objects (unlocked_problems M2M, highest_unlocked_order) without wrapping in `transaction.atomic()`. A failure partway through could leave TeamProgress in an inconsistent state.

3. **No concurrency handling** - Two simultaneous accepted submissions for the same team could both try to unlock the same next problem, or both read the same `highest_unlocked_order` before either writes.

4. **Tight JS coupling in submission controller** - Directly querying the DOM for the editor controller breaks Stimulus conventions. Should use Stimulus outlets:
   ```javascript
   static outlets = ["monaco-editor"]
   // then: this.monacoEditorOutlet.getCode()
   ```

5. **Magic numbers** - The initial unlock count of 6 is hardcoded in `signals.py`, `seed_testdata.py`, and the tests. Should be a constant (e.g., `INITIAL_UNLOCK_COUNT = 6`) or a field on Competition.

6. **Missing `__str__` on some models** - Competition and Submission lack `__str__` methods, which makes Django admin and debugging harder.

### 7.3 Trojsten Scaffold Alignment

The `CLAUDE.md` references `trojsten/django-scaffold` but this repository does not appear to exist publicly. The project follows inferred Trojsten conventions:

| Convention | Followed? | Notes |
|---|---|---|
| Apps inside project package | Yes | |
| Service layer (`services.py`) | Yes | |
| Signal layer (`signals.py`) | Yes | |
| AppConfig with explicit labels | Yes | |
| `environs` for settings | Yes | |
| `ruff` for linting | Yes | |
| `pre-commit` hooks | Yes | Config exists |
| `trojsten/django-docker` base image | Yes | |
| `uv` for Python package management | Yes | |

**Deviation:** The `CLAUDE.md` describes the structure as `naboj/apps/competition/` but the actual structure is `ksp-naboj/competition/` (apps at project root, not in `apps/` subdirectory). The `CLAUDE.md` should be updated to match reality.

---

## 8. Prioritized Action Items

### P0 - Blockers (Fix Before Any Demo)

| # | Issue | Location | Effort |
|---|---|---|---|
| 1 | **Register signals in `ready()`** | `team/apps.py` | 2 min |
| 2 | **Remove `@csrf_exempt`** from submit_code | `submission/views.py` | 5 min |
| 3 | **Add `json.loads` error handling** in submit_code | `submission/views.py` | 5 min |
| 4 | **Add competition time-window check** in submit_code | `submission/views.py` | 10 min |
| 5 | **Check problem is unlocked** before accepting submission | `submission/views.py` | 15 min |

### P1 - High Priority (Before User Testing)

| # | Issue | Location | Effort |
|---|---|---|---|
| 6 | Team name unique per competition, not globally | `team/models.py` | 15 min + migration |
| 7 | Wrap `handle_successful_submission` in `transaction.atomic()` | `team/services.py` | 5 min |
| 8 | Add `select_for_update()` for TeamProgress in submission handler | `team/services.py` | 10 min |
| 9 | Use `json_script` filter instead of `{{ json\|safe }}` | `competition.html` | 5 min |
| 10 | Add `LoginRequiredMixin` / `@login_required` | views | 10 min |
| 11 | Derive team from authenticated user, not query param | `competition/views.py` | 30 min |
| 12 | Build timer controller (Part 6.2, 6.3) | JS + template | 2 hrs |
| 13 | Add localStorage persistence for editor code | `monaco-editor_controller.js` | 30 min |
| 14 | Sanitize markdown output with DOMPurify | `problem-statement_controller.js` | 15 min |

### P2 - Medium Priority (Before Competition Day)

| # | Issue | Location | Effort |
|---|---|---|---|
| 15 | Implement htmx problem-list refresh after submission (Part 7.1) | views + templates | 2 hrs |
| 16 | Add submission blocking/cooldown mechanic | models + services | 4 hrs |
| 17 | Implement score tracking and update `TeamProgress.score` | services | 1 hr |
| 18 | Add scoreboard view with tiebreaker logic | new view + template | 4 hrs |
| 19 | Create `TeamMembership` model linking User to Team | models + migration | 2 hrs |
| 20 | Extract magic number 6 to constant/setting | multiple files | 15 min |
| 21 | Add `app_name` to URL confs for namespacing | all `urls.py` | 10 min |
| 22 | Add tests for `get_problem_groups` and `get_unlocked_problems_json` | `competition/tests.py` | 2 hrs |
| 23 | Add tests for `submit_code` view | `submission/tests.py` | 2 hrs |
| 24 | Use Stimulus outlets instead of DOM queries in submission controller | `submission_controller.js` | 30 min |

### P3 - Low Priority (Polish)

| # | Issue | Location | Effort |
|---|---|---|---|
| 25 | Consider renaming `ksp-naboj/` to `ksp_naboj/` to fix imports | project-wide | 2 hrs |
| 26 | Add `__str__` to Competition and Submission models | models | 5 min |
| 27 | Add responsive/mobile layout (Part 8.1) | templates + CSS | 4 hrs |
| 28 | Add empty states for competition not started/ended (Part 8.2) | templates | 1 hr |
| 29 | Add loading states and skeletons (Part 8.3) | templates + JS | 2 hrs |
| 30 | Make HSTS conditional on `not DEBUG` | `settings.py` | 2 min |
| 31 | Add custom managers for common query patterns | models | 1 hr |
| 32 | Remove unused `item` target from problem-list controller | JS | 1 min |
| 33 | Update `CLAUDE.md` to match actual project structure | docs | 15 min |

---

## Appendix A: FRONTEND-PLAN Part Completion Status

| Part | Description | Status | Notes |
|---|---|---|---|
| 1 | Foundation | **Complete** | Views, URLs, base template |
| 2 | Problem List Sidebar | **Complete** | Grouped problems with status indicators |
| 3 | Problem Statement Panel | **Complete** | Markdown rendering, XSS concern |
| 4 | Monaco Editor | **Complete** | Code editing, language switching, code store |
| 5 | Submission Flow (Mock) | **Complete** | POST submit, mock judging, feedback |
| 6 | Timer and Header Bar | **Partial** | Model fields done; controller + UI missing |
| 7 | Dynamic Updates (htmx) | **Not Started** | Critical for real-time UX |
| 8 | Polish and Edge Cases | **Not Started** | Important before competition |

## Appendix B: Django Best Practice Checklist

| Category | Practice | Applied? |
|---|---|---|
| **Models** | Use `choices` for enumerated fields | Yes |
| | Use `unique_together` / `UniqueConstraint` | Partial |
| | Define `__str__` on all models | Partial |
| | Use `get_absolute_url()` | No |
| | Avoid raw SQL unless necessary | Yes |
| **Views** | Use class-based views for standard patterns | Yes |
| | Use `get_object_or_404` | Yes |
| | Validate and clean all input | No |
| | Apply proper permission checks | No |
| **Forms** | Use Django forms for validation | Partial (no form for submissions) |
| | Use ModelForm when possible | N/A yet |
| **Security** | CSRF protection on all state-changing views | **No** |
| | Login required where appropriate | **No** |
| | XSS prevention | Partial |
| | SQL injection prevention (ORM) | Yes |
| **Testing** | Test business logic thoroughly | Yes (unlock logic) |
| | Test views | No |
| | Test edge cases | Yes (unlock edge cases) |
| **Performance** | Use `select_related`/`prefetch_related` | Partial |
| | Avoid N+1 queries | Partial |
| | Use database indexes | No custom indexes |
| **Code Quality** | Use type hints | No |
| | Use constants for magic values | No |
| | Use linting (ruff) | Yes |
