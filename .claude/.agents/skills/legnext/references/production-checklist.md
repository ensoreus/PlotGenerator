# Production Checklist

Run through this before shipping a Legnext integration. Each item is a concrete, checkable thing.

## Auth & config
- [ ] API key read from an environment variable (`LEGNEXT_API_KEY`), never hardcoded or committed.
- [ ] `.gitignore` / secret scanner excludes the key. No key in code, logs, or error messages.
- [ ] Base URL is configurable (default `https://api.legnext.ai`) so tests can point elsewhere.
- [ ] `x-api-key` sent on submit/account requests; never sent or exposed from browser code.
- [ ] Get Task capability URL kept server-side; no API key is required for it.
- [ ] Using the correct environment's key (a key for one environment will not work against another).

## Submitting
- [ ] Prompt length validated (1–8192 chars) before submit.
- [ ] **Model version pinned explicitly** with `--v` whenever it matters (no-`--v` renders as v7).
- [ ] Flags validated against the chosen version (no `--cref`/`--oref`/`--q`/`--turbo` on v8.1/v8.2; no `--draft` on v8.0).
- [ ] `callback` set only when you have a reachable HTTPS webhook endpoint.
- [ ] `job_id` from the response persisted **before** considering the submit successful.

## Waiting
- [ ] **Polling**: bounded wait and non-zero interval; terminal states (`completed`/`failed`) break the loop; `pending`/`staged`/`processing`/`retry` keep polling.
- [ ] **Webhook**: endpoint is public HTTPS; responds `2xx` fast; **dedupes by `job_id`**; fetches the canonical result via `GET /api/v1/job/{job_id}` rather than trusting the callback body alone.
- [ ] Polling remains a recovery path when callbacks are used.
- [ ] Callback handler does not assume a public signing secret exists; validates shape and fetches Get Task.

## Fetching & storing
- [ ] On `completed`, read `output.image_url` (primary) and `output.image_urls` (grid).
- [ ] **Download images to permanent storage immediately** (your own bucket/disk) - CDN URLs expire in **30 days**.
- [ ] Image download sets an explicit `User-Agent` - the CDN 403s `Python-urllib/*` (bot mitigation).
- [ ] If upscaling/varying later, done within **3 days** of the parent job's creation.
- [ ] `output.seed` persisted if reproducibility matters.

## Child tasks
- [ ] Read `output.available_actions` as guidance for actions + `imageNo`.
- [ ] Child submitted with parent `job_id` + `imageNo` (0–3).
- [ ] Handle *"re-generate the base image and retry"* / *"not supported for the selected image"* by regenerating the base image, not by looping.
- [ ] `available_actions` treated as advisory (may over-advertise for edit-derived images); 4xx handled gracefully.

## Credits & billing
- [ ] On `402`, surface a top-up prompt; check `GET /api/account/balance`; do not silently retry.
- [ ] Read cost from `meta.usage.frozen`/`consume` in the response - no hardcoded price table.

## Errors & retries
- [ ] Per-class handling implemented (see `errors.md`): auth, quota, rate, moderation, validation, action-not-supported, transient.
- [ ] **Retriable only** `429`/`5xx`/network/timeout, with exponential backoff.
- [ ] **Never retry** `400/401/402/403` or moderation/action errors unchanged.
- [ ] Retries are idempotent on your side (dedupe by `job_id`); a re-submit creates a new billed job.

## Observability
- [ ] Log `job_id`, `task_type`, status transitions, and `error.code`/`error.message` for every job.
- [ ] Distinguish **user errors** (moderation, quota, validation) from **service errors** (5xx, empty error, timeout) in metrics/alerts - don't page on user errors.
- [ ] Outage heuristic: alert when failures spike across many unrelated jobs with empty/generic errors (likely transient upstream).

## Security
- [ ] Webhook callback URL is HTTPS and uses an unguessable path.
- [ ] Inbound webhook handler does not trust the body as canonical; it fetches Get Task by `job_id`.
- [ ] User-supplied prompts/URLs treated as untrusted data (no eval, no SSRF from `--sref`/`--oref`/`--cref` image URLs you fetch).

## Smoke test before go-live
- [ ] Submit one `diffusion` task, poll to `completed`, download the image, verify it opens.
- [ ] Submit one child task (e.g. `upscale`) on the result, verify it completes.
- [ ] Trigger one moderation/validation error and confirm your handler classifies it correctly (no retry storm).
- [ ] Confirm a `402`/low-balance path surfaces a top-up prompt.
