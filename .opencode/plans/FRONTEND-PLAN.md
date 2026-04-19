# Frontend Implementation Plan - Competition Interface

## Layout Overview

The competition page uses a **12-column grid** below the navbar:

```
| Problem List (2 cols) | Problem Statement (3 cols) | Code Editor (7 cols) |
```

- Problem list: grouped by title, with easy/hard sub-rows per group
- Problem statement: markdown rendered with `marked.js`
- Code editor: Monaco Editor (bundled via esbuild)

## Development Commands

```bash
# Docker: start all services
docker compose up -d

# Docker: run management commands
docker compose exec web python manage.py <command>

# Docker: run migrations
docker compose exec web python manage.py migrate

# Docker: seed test data (creates competition, problems, team)
docker compose exec web python manage.py seed_testdata

# Django system check
uv run python manage.py check

# Run dev server (local, not Docker)
uv run python manage.py runserver

# Frontend watch (TailwindCSS + esbuild) - needed locally for JS changes
pnpm watch

# Frontend build
pnpm build

# Lint
uvx ruff check ksp-naboj/

# Install new JS dependencies
pnpm add <package>

# Note: static files (app.js, app.css) are mounted into Docker via volume
# ./ksp-naboj -> /app/ksp-naboj, so local pnpm build is reflected immediately.
# The tailwind service handles CSS watching inside Docker.
```

## Test Data

After running `seed_testdata`, visit:
- **http://localhost:8000/competition/2026/?team_id=2**

This creates:
- 8 problem groups (easy + hard each), unlock_order 1-8
- First 6 easy problems unlocked
- Hard variants for groups 1-2 unlocked
- Faktorial easy marked as solved (accepted submission)

## Architecture Decisions

- **Layout**: Keep standard navbar from `base.html`, competition fills remaining viewport height (`h-[calc(100vh-navbar)]`)
- **Monaco Editor**: Install via `pnpm add monaco-editor`, bundle with esbuild
- **Markdown**: `marked.js` for client-side rendering
- **Interactivity**: Stimulus controllers for editor, problem selection, markdown rendering
- **Dynamic updates (future)**: htmx partials for problem list, submission status, timer

---

## Part 1: Foundation - Views, URLs, and Base Template

**Goal**: Get a working Django view serving the competition page with the correct layout grid.

### Tasks

- [ ] **1.1 Add django-htmx middleware** to `settings.py` MIDDLEWARE
- [ ] **1.2 Create `CompetitionDetailView`** in `ksp-naboj/competition/views.py`
  - Takes competition `year` from URL
  - Gets the team for the current user (via `Team.members` or a new FK)
  - Passes competition, team, team progress (unlocked problems) to template
  - Note: Auth is not wired yet, so for now accept a `team_id` query param for development
- [ ] **1.3 Wire up URLs**
  - `ksp-naboj/competition/urls.py`: `path("<int:year>/", CompetitionDetailView.as_view(), name="competition-detail")`
  - Include competition URLs in `ksp-naboj/urls.py`
- [ ] **1.4 Create base competition template** `ksp-naboj/competition/templates/competition/competition.html`
  - Extends `base.html`, overrides `outer_container` block
  - Full-width grid: `grid grid-cols-12 gap-0 h-[calc(100vh-4rem)]`
  - Three placeholder columns (2+3+7) with borders/dividers
  - No content yet, just the structural skeleton

### Files Modified
- `ksp-naboj/settings.py` - add django-htmx middleware
- `ksp-naboj/competition/views.py` - new view
- `ksp-naboj/competition/urls.py` - add URL pattern
- `ksp-naboj/urls.py` - include competition URLs
- `ksp-naboj/competition/templates/competition/competition.html` - new template

---

## Part 2: Problem List Sidebar (2 cols)

**Goal**: Render the problem list with grouped easy/hard sub-rows, visual status indicators.

### Tasks

- [ ] **2.1 Add a service method** to get unlocked problems grouped by unlock_order
  - In `ksp-naboj/competition/services.py` (new file) or `problem/services.py`
  - Returns problems ordered by `unlock_order`, grouped into `[(title, [easy_problem, hard_problem]), ...]`
  - Mark which are unlocked vs locked (grayed out) based on `TeamProgress.unlocked_problems`
  - Mark which are solved (have an `accepted` submission from the team)
- [ ] **2.2 Create problem list template partial** `competition/partials/_problem_list.html`
  - Each group: header row with title and unlock order number
  - Two sub-rows: "Easy" and "Hard" with difficulty badge
  - Visual states:
    - **Unlocked + unsolved**: clickable, default styling
    - **Unlocked + solved**: green checkmark badge
    - **Locked**: grayed out, lock icon, not clickable
  - Currently selected problem highlighted with `bg-primary/10` or similar
- [ ] **2.3 Add Stimulus controller** `problem-list_controller.js`
  - Tracks currently selected problem ID
  - On click: updates selection state, dispatches event for other panels to react
  - For now: just adds/removes active class on click (no server round-trip)

### Files Modified
- `ksp-naboj/competition/services.py` - new service for grouped problems
- `ksp-naboj/competition/templates/competition/partials/_problem_list.html` - new partial
- `ksp-naboj/styles/src/controllers/problem-list_controller.js` - new Stimulus controller
- `ksp-naboj/competition/templates/competition/competition.html` - integrate sidebar

---

## Part 3: Problem Statement Panel (3 cols) ✅

**Goal**: Display the selected problem's description rendered from markdown.

### Tasks

- [x] **3.1 Install marked.js**: `pnpm add marked`
- [x] **3.2 Add `get_unlocked_problems_json()` to services.py**
  - Returns `{id: {title, difficulty, description, language}}` for unlocked problems only
  - Serialized as JSON in view context
- [x] **3.3 Create Stimulus controller** `problem-statement_controller.js`
  - Reads shared JSON from page-level `<script type="application/json" id="problems-data">`
  - Listens for `problem:select` on `window`
  - Renders markdown via `marked.parse()` into `prose`-styled container
  - Toggles placeholder/content visibility
- [x] **3.4 Create problem statement partial** `competition/partials/_problem_statement.html`
  - Placeholder div when no problem selected
  - Content div with title, difficulty badge, rendered markdown
- [x] **3.5 Update competition.html**
  - Added shared `<script type="application/json" id="problems-data">` at page level
  - Replaced 3-col placeholder with partial include

### Files Modified
- `package.json` - add `marked` dependency
- `ksp-naboj/styles/src/controllers/problem-statement_controller.js` - new Stimulus controller
- `ksp-naboj/competition/templates/competition/partials/_problem_statement.html` - new partial
- `ksp-naboj/competition/templates/competition/competition.html` - integrate statement panel

---

## Part 4: Monaco Editor Integration (7 cols)

**Goal**: Embed Monaco Editor in the right panel, wired to the selected problem.

### Tasks

- [ ] **4.1 Install Monaco Editor**: `pnpm add monaco-editor`
- [ ] **4.2 Create Stimulus controller** `monaco-editor_controller.js`
  - Creates Monaco editor instance on `connect()`
  - Configurable via values: `language` (default: `python`), `theme` (default: `vs-dark`)
  - Provides methods: `getCode()`, `setCode()`, `setLanguage()`
  - Handles resize when panel dimensions change (via `ResizeObserver`)
  - **Important**: Monaco's web workers need special handling with esbuild. Use `esbuild-plugin-monaco-editor` or configure workers manually via `self.MonacoEnvironment`
- [ ] **4.3 Update esbuild config** `ksp-naboj/styles/src/build.mjs`
  - Add Monaco editor plugin or configure worker bundling
  - Monaco workers needed: `editorWorker`, `typescript`, `json` (as needed)
- [ ] **4.4 Create editor panel partial** `competition/partials/_editor_panel.html`
  - Full-height container for Monaco
  - Language selector dropdown above the editor
  - Submit button below the editor
  - Uses the `monaco-editor` Stimulus controller
- [ ] **4.5 Wire problem selection to editor**
  - When problem changes: update language restriction if any, optionally reset editor content
  - Store per-problem code in memory (JS Map) so switching problems preserves work

### Files Modified
- `package.json` - add `monaco-editor` dependency
- `ksp-naboj/styles/src/build.mjs` - configure Monaco workers
- `ksp-naboj/styles/src/controllers/monaco-editor_controller.js` - new Stimulus controller
- `ksp-naboj/competition/templates/competition/partials/_editor_panel.html` - new partial
- `ksp-naboj/competition/templates/competition/competition.html` - integrate editor panel

---

## Part 5: Submission Flow (Mock)

**Goal**: Allow submitting code from the editor and displaying results.

### Tasks

- [ ] **5.1 Create submission view** in `ksp-naboj/submission/views.py`
  - `POST /competition/<year>/submit/` with `problem_id`, `code`, `language`
  - Creates a `Submission` object with status `pending`
  - For now: mock the result (randomly accept/reject after a short delay) OR just create as `pending`
  - Returns submission result as JSON (for htmx/fetch consumption)
- [ ] **5.2 Wire submission URLs** in `ksp-naboj/submission/urls.py`
- [ ] **5.3 Create submission Stimulus controller** `submission_controller.js`
  - Handles submit button click
  - POSTs code + language + problem_id to submission endpoint
  - Shows loading state on submit button
  - Displays result (accepted/rejected/error) in a toast or inline message
- [ ] **5.4 Add submission feedback UI** to editor panel
  - Toast/notification for submission result
  - Recent submissions list below editor or in a collapsible panel
  - Status badges: green for accepted, red for rejected, yellow for pending

### Files Modified
- `ksp-naboj/submission/views.py` - new submission view
- `ksp-naboj/submission/urls.py` - add URL pattern
- `ksp-naboj/urls.py` - include submission URLs
- `ksp-naboj/styles/src/controllers/submission_controller.js` - new Stimulus controller
- `ksp-naboj/competition/templates/competition/partials/_editor_panel.html` - add submit button and feedback

---

## Part 6: Competition Timer and Header Bar

**Goal**: Add a timer showing remaining time and competition status in a header bar.

### Tasks

- [ ] **6.1 Add competition timing fields** to `Competition` model (or a new `CompetitionRound` model)
  - `start_at` (DateTimeField)
  - `end_at` (DateTimeField, computed as `start_at + 2 hours`)
  - Migration
- [ ] **6.2 Create timer Stimulus controller** `timer_controller.js`
  - Takes `endTime` value (ISO string)
  - Countdown display: `HH:MM:SS`
  - Uses `stimulus-use` `useIntersection` or simple `setInterval`
  - Triggers "time-up" event when timer reaches zero
- [ ] **6.3 Add timer bar** to competition template
  - Between navbar and grid: slim bar with timer on right, competition title on left
  - Score display (problems solved count)

### Files Modified
- `ksp-naboj/competition/models.py` - add timing fields
- `ksp-naboj/styles/src/controllers/timer_controller.js` - new Stimulus controller
- `ksp-naboj/competition/templates/competition/competition.html` - add timer bar

---

## Part 7: Dynamic Updates with htmx

**Goal**: Enable real-time updates without full page refreshes.

### Tasks

- [ ] **7.1 Problem unlock updates**
  - After successful submission triggers unlock (via `team/services.py`)
  - htmx polling or SSE to check for new unlocked problems
  - htmx partial endpoint: `GET /competition/<year>/problem-list/` returns the problem list HTML
  - Auto-refresh problem list every 10s or after each submission
- [ ] **7.2 Submission status polling**
  - After submitting, poll for status changes (`pending` -> `accepted`/`rejected`)
  - htmx partial: `GET /submission/<id>/status/` returns status badge HTML
  - Use htmx `hx-trigger="every 2s"` on the status element until resolved
- [ ] **7.3 Score updates**
  - After accepted submission, update score display
  - htmx oob-swap to update score in header bar
- [ ] **7.4 Future: WebSocket/SSE for team coordination**
  - Show which teammates are viewing which problem
  - Live submission feed within the team
  - Not in initial implementation, but architecture should support it

### Files Modified
- `ksp-naboj/competition/views.py` - add problem list partial view
- `ksp-naboj/submission/views.py` - add submission status view
- `ksp-naboj/competition/templates/competition/partials/_problem_list.html` - add htmx attributes
- `ksp-naboj/competition/templates/competition/competition.html` - add htmx polling

---

## Part 8: Polish and Edge Cases

**Goal**: Handle edge cases, improve UX, add visual polish.

### Tasks

- [ ] **8.1 Responsive behavior**: On narrow screens, stack panels vertically or use tabs
- [ ] **8.2 Empty states**: No problems unlocked, competition not started, competition ended
- [ ] **8.3 Loading states**: Skeleton loading for problem statement, spinner for submissions
- [ ] **8.4 Error handling**: Network errors on submission, Monaco load failures
- [ ] **8.5 Dark mode**: Monaco is `vs-dark`, ensure sidebar and statement match
- [ ] **8.6 Accessibility**: Keyboard navigation for problem list, ARIA labels
- [ ] **8.7 Code preservation**: Warn before navigating away with unsaved code in editor

---

## Dependency Install Summary

```bash
pnpm add monaco-editor marked
```

No additional Python packages needed (django-htmx is already installed).

## Key File Map After Implementation

```
ksp-naboj/
├── competition/
│   ├── views.py                          # CompetitionDetailView + partial views
│   ├── urls.py                           # Competition URL patterns
│   ├── services.py                       # Business logic for grouped problems
│   └── templates/competition/
│       ├── competition.html              # Main competition page (extends base.html)
│       └── partials/
│           ├── _problem_list.html        # Problem sidebar
│           ├── _problem_statement.html   # Markdown problem view
│           └── _editor_panel.html        # Monaco editor + submit
├── submission/
│   ├── views.py                          # Submit view + status polling
│   └── urls.py                           # Submission URL patterns
└── styles/
    └── src/
        ├── build.mjs                     # Updated for Monaco workers
        └── controllers/
            ├── problem-list_controller.js
            ├── problem-statement_controller.js
            ├── monaco-editor_controller.js
            ├── submission_controller.js
            └── timer_controller.js
```

## Data Flow Diagram

```
[Page Load]
    │
    ├── CompetitionDetailView
    │   ├── competition, team, team_progress
    │   ├── unlocked_problems (grouped by title)
    │   └── competition timing (start_at, end_at)
    │
    ├── Problem List (Stimulus)
    │   └── click -> dispatches "problem:select" event
    │
    ├── Problem Statement (Stimulus)
    │   └── listens "problem:select" -> renders markdown
    │
    ├── Monaco Editor (Stimulus)
    │   └── listens "problem:select" -> switches language/content
    │
    └── Submit Button (Stimulus)
        └── POST /submit/ -> shows result -> triggers problem list refresh
```

## Estimated Effort

| Part | Description | Complexity | Dependencies |
|------|-------------|------------|--------------|
| 1 | Foundation (views, URLs, template) | Low | None |
| 2 | Problem list sidebar | Medium | Part 1 |
| 3 | Problem statement (markdown) | Low | Part 2, pnpm add marked |
| 4 | Monaco Editor | High | Part 2, pnpm add monaco-editor |
| 5 | Submission flow | Medium | Parts 1-4 |
| 6 | Timer | Low | Part 1, model changes |
| 7 | htmx dynamic updates | Medium | Parts 1-5 |
| 8 | Polish | Low-Medium | All previous |

**Recommended implementation order**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
