# Errors and recovery

Do not branch on exact provider sentences. Use HTTP status and broad failure
class, then retain the sanitized error object for diagnostics.

| Signal | Action |
|---|---|
| `400` | Fix fields, flags, model/action compatibility, or moderated input |
| `401` | Correct or replace the API key |
| `402` | Ask the user to top up before resubmitting |
| `403` | Correct account/content restrictions or contact support |
| `404` Get Task | Check the capability URL; the task may have expired |
| `429` | Wait for running work, then retry with backoff |
| transient `5xx` / network failure | Retry with capped exponential backoff and jitter |
| persistent `5xx` | Stop and contact support with `job_id` |
| task `failed` | Classify `error`; resubmit only when transient |

Task endpoint failures use the TaskResponse error object:

```json
{
  "status": "failed",
  "error": {
    "code": 400,
    "message": "Human-readable failure",
    "raw_message": "Optional provider detail",
    "detail": null
  }
}
```

Keep `raw_message` in restricted server logs. Do not expose it directly to end
users.

Legnext does not provide a submit idempotency key. Retrying a POST can create a
new billable task. Persist returned identifiers and dedupe processing by
`job_id`.

Current reference:
https://docs.legnext.ai/api-reference/errors
