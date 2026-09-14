# Models and parameters

Do not copy a parameter matrix into generated code or agent context. The
backend-generated contract is the authority:

- Human matrix: https://docs.legnext.ai/getting-started/image-parameters
- Machine schema: https://docs.legnext.ai/schemas/mj-image-params.v1.json
- Model choices: https://docs.legnext.ai/getting-started/models
- Video controls: https://docs.legnext.ai/getting-started/video-parameters

## Stable integration rules

- Put Midjourney flags in the prompt text.
- Pin `--v` when output behavior or parameter compatibility matters.
- When `--v` is omitted, the Legnext API currently uses V7.
- Validate the full flag combination against the machine schema before
  submitting.
- Read actual usage from `meta.usage`; do not hardcode credit prices.
- Use the OpenAPI request schema for JSON fields. Prompt-parameter docs do not
  replace the endpoint contract.

Example:

```text
Cinematic coastal road at sunrise --v 8.2 --ar 16:9
```
