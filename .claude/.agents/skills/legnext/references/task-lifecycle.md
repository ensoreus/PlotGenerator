# Task lifecycle

Legnext media operations are asynchronous:

```text
submit → persist job_id → poll or receive callback → terminal state → save output
```

## Base URL and authentication

- Base URL: `https://api.legnext.ai`
- Submit endpoints: `POST /api/v1/{endpoint}` with `x-api-key`
- Account endpoints: `/api/account/{endpoint}` with `x-api-key`
- Get Task: `GET /api/v1/job/{job_id}` without an API key

The Get Task UUID is a capability token. Keep it server-side and out of browser
URLs, analytics, screenshots, and public logs.

## Submit

Use the generated OpenAPI contract at
`https://docs.legnext.ai/openapi.yaml` for exact request fields. A successful
submit returns a TaskResponse and `job_id`. Persist the identifier before
starting a wait or acknowledging work to the caller.

Credits are reserved at submit (`meta.usage.frozen`), consumed on success
(`meta.usage.consume`), and released on failure.

## Statuses

| Status | Client action |
|---|---|
| `pending` | Continue waiting |
| `staged` | Continue waiting; queued behind account concurrency |
| `processing` | Continue waiting |
| `retry` | Continue waiting; Legnext is resubmitting internally |
| `completed` | Persist the output |
| `failed` | Classify the error; retry only if transient |

`completed` and `failed` are terminal.

## Polling

Poll `GET /api/v1/job/{job_id}` with a non-zero interval and a bounded client
wait. Do not send the API key. A client timeout does not cancel the server task;
resume the same `job_id` from a worker instead of submitting a replacement.

## Callback

Pass `callback` at submission when the application has a durable event
processor.

- Respond quickly and process asynchronously.
- Expect duplicate, delayed, or missing delivery.
- Dedupe by `job_id`.
- Fetch Get Task as the canonical result.
- Keep polling as recovery.

Task callbacks do not currently provide a public signing secret. Use an
unguessable endpoint path, validate the request shape, and do not treat the
callback body alone as trusted state.

## Retention

- Task lookup and parent-dependent actions are available for three days.
- Output delivery URLs are retained for no more than 30 days.
- Download completed output immediately to application-owned storage.

`available_actions` is advisory. A provider can still reject an advertised
follow-up action; handle that `400` without looping on the same parent.

## Duplicate submits

Legnext has no submit idempotency key and does not deduplicate by prompt. A
repeated POST can create another billable task. Use an application operation ID
or database constraint, and persist every returned `job_id`.

If the connection fails before a submit response arrives, the outcome is
ambiguous. Decide whether a possible duplicate is preferable to dropping the
user request; do not claim exactly-once behavior.

## Current reference

- Lifecycle: https://docs.legnext.ai/getting-started/task-lifecycle
- Get Task: https://docs.legnext.ai/api-reference/task-management/get-task
- Output storage: https://docs.legnext.ai/getting-started/output-storage
