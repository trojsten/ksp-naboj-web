# Judge Integration: Status & Remaining Work

> **Scope:** Integrate real Trojsten Judge (`judge.ksp.sk`) for submitting and
> judging competition solutions. Replaces the previous mock judging.

---

## Current state (done)

Submissions now go to the real judge and results are pulled back on-demand.

### Submit path
- [x] `judge-client` (git) dependency + `requests` (transitive) in `pyproject.toml`
- [x] Settings: `JUDGE_TOKEN` (from `JUDGE_SECRET`), `JUDGE_URL`,
      `JUDGE_NAMESPACE` (env-var precedence, falls back to
      `Competition.judge_namespace`), `USE_MOCK_JUDGE` (auto-on when no token)
- [x] `Submission` model: `judge_public_id`, `protocol_key` fields + migration
      (`0003_submission_judge_public_id_and_more`)
- [x] `submission/services.py`:
  - `get_judge_client()` (cached)
  - `LANGUAGE_EXTENSIONS` + `filename_for()` (Monaco lang → `solution.<ext>`)
  - `submit_to_judge()` — calls `client.submit(task, namespace, external_user_id, ...)`
- [x] `submission/views.py:submit_code` branches on `USE_MOCK_JUDGE`; real mode
      calls `submit_to_judge()` and leaves status `pending`; failures are
      classified (`TaskNotFoundError`→422, `UnknownLanguageError`→422,
      `JudgeConnectionError`→502) and logged with traceback
- [x] Frontend (`submission_controller.js`) shows "Submitted — waiting for
      result." for pending submits

### Result path (on-demand fetch / polling)
- [x] `submission/services.py`:
  - `refresh_from_judge()` — `get_submit(public_id)`, applies when `FINISHED`,
        no-op otherwise, swallows errors
  - `apply_judge_result()` — verdict→status map, max CPU time, **idempotent**
        unlock on `OK` (full-OK only; `POK` does not unlock)
  - helpers: `_submit_status_code`, `_verdict_code`, `_max_cpu_time_seconds`
- [x] `GET /competition/status/<judge_public_id>/` endpoint — team-scoped,
      on-demand fetch when still pending
- [x] Frontend polls `/competition/status/` every 2s (up to ~3 min) after a
      pending submit, then shows the verdict
- [x] Verdict map validated against real judge data
      (`1d5258f739623cba` → `OK` → `accepted`, 0.106s)
- [x] Tests: submit, verdict mapping, unlock, idempotency, refresh
      (60 total, 2 pre-existing unrelated failures)

### Mock fallback
- [x] `USE_MOCK_JUDGE=True` keeps the synchronous random verdict for dev/CI
      without judge access; auto-enabled when `JUDGE_SECRET` is empty

---

## Remaining work

### 1. Webhook receiver (post-deploy) — replaces polling as primary path
Currently results are pulled on-demand by the frontend polling our status
endpoint (one judge HTTP request per poll per pending submission). Once
deployed with a public URL, the judge can push results to a webhook — cheaper
and truly real-time.

- [ ] Add `JUDGE_WEBHOOK_TOKEN` setting (shared secret to verify the webhook
      payload's `token` field)
- [ ] Add `Submission` fields for full result storage (one migration):
      `judge_status` (queued/finished/failed), `testing_status`
      (waiting/pulling_image/testing/done), `protocol` (JSONField)
- [ ] Create webhook view `POST /competition/webhooks/judge/`:
      - `@csrf_exempt`
      - verify `payload["token"] == settings.JUDGE_WEBHOOK_TOKEN`
      - look up `Submission` by `judge_public_id == payload["public_id"]`
      - build a Submit-shaped object from the payload and call
            `apply_judge_result(submission, submit)` (already idempotent)
      - return 200
- [ ] Email judge@ksp.sk to configure the webhook URL + token on their side
- [ ] Keep the status endpoint + frontend polling as a fallback (it returns
      terminal instantly once the webhook has updated the DB)
- [ ] Optionally lower/remove the on-demand fetch in the status endpoint once
      the webhook is reliable (keep it gated on `status == PENDING`)

### 2. Protocol display (optional UX improvement)
Right now teams see only the final verdict + time. The judge ships a JS lib
(`protocol-embed`) that renders per-testcase results in an iframe for free.

- [ ] Add `<script async src="https://judge.ksp.sk/static/js/protocol-embed.min.js">`
      to `base.html`
- [ ] On a finished submission, render
      `<judge-embed-protocol protocol-key="{{ submission.protocol_key }}">`
      in the result UI
- [ ] `Submission.protocol_key` is already stored, so no model change needed

### 3. Real task data
The integration works, but `Problem.judge_task` must match real task slugs in
the configured namespace. Seeded values (`naboj-2026-1a`) are synthetic.

- [ ] Map each `Problem` (easy→`_a`, hard→`_b`) to a real task slug
      (e.g. `pr-8-2026-najcastejsi-znak_a`) via admin
- [ ] **OR** author + upload tasks into your own namespace (e.g. `test-2026`,
      currently empty) via `judge_client.create_task()` +
      `upload_task_data()` — needs statements/testcases/solutions
- [ ] Optional: management command `validate_judge_tasks` that lists
      `Problem`s whose `judge_task` is **not** found in the judge (calls
      `get_tasks(namespace=...)`), to catch mismatches before the competition
- [ ] Update `seed_testdata.py` to real slugs once the mapping is known

### 4. Production hardening
- [ ] Decide unlock semantics for partial credit (`POK`) — currently treated as
      rejected (full-OK only). Revisit if partial scoring is desired.
- [ ] Consider a per-submission judge-call throttle in the status endpoint
      (e.g. `last_judge_fetch_at` field, skip re-fetch within 1s) if polling
      load on the judge becomes a concern before the webhook lands
- [ ] Sentry: uncomment + wire `SENTRY_DSN` in `settings.py` for judge-error
      visibility in production
- [ ] Status semantics: failed-to-submit is currently stored as `rejected`.
      Consider a distinct `submission_failed` status if clearer reporting is
      needed (currently out of scope — `error_message` carries the reason)

### 5. Out-of-band issues found (not judge-related, pre-existing)
- [ ] `ksp-naboj/problem/tests.py::test_problem_language_optional` fails
      (expects `language is None`, model has `default=""`)
- [ ] `ksp-naboj/team/tests.py::test_team_progress_str_representation` fails
      (expects default `__str__`, model has a custom one)

---

## Key files

| File | Role |
|---|---|
| `ksp-naboj/submission/services.py` | judge client, submit, refresh, verdict mapping, unlock trigger |
| `ksp-naboj/submission/views.py` | `submit_code`, `submission_status`, error classification |
| `ksp-naboj/submission/models.py` | `Submission` (+ `judge_public_id`, `protocol_key`) |
| `ksp-naboj/competition/urls.py` | `submit/`, `status/<public_id>/` routes |
| `ksp-naboj/settings.py` | `JUDGE_TOKEN`, `JUDGE_URL`, `JUDGE_NAMESPACE`, `USE_MOCK_JUDGE` |
| `ksp-naboj/styles/src/controllers/submission_controller.js` | submit + poll UI |

## Configuration (`/competition/submit/` + status endpoint)

| Env var | Purpose | Default |
|---|---|---|
| `JUDGE_SECRET` | API token (`X-API-Token`) | — (empty → mock mode) |
| `JUDGE_URL` | Judge base URL | `https://judge.ksp.sk` |
| `JUDGE_NAMESPACE` | Namespace for all submits | falls back to `Competition.judge_namespace` |
| `USE_MOCK_JUDGE` | Force mock judging | auto: `not JUDGE_SECRET` |
