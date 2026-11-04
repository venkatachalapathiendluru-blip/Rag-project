# Security

**Intended deployment: one trusted user on a local machine.** The stack binds to `127.0.0.1`. It is not ready for the public internet as it stands.

## In place

| Area | Control | Verified by |
|---|---|---|
| Secrets | Environment only. `.env` is excluded by an allowlist `.gitignore` and `.dockerignore` | File scan, browser check of page, config and bundles |
| Browser | No provider keys. `/config/` reports only whether a key is set | Integration and browser tests |
| Input | Pydantic validation, unknown fields rejected, question length limit | Tests |
| SQL | Parameterised queries throughout | Code review |
| Uploads | Type allowlist, content check, size and page limits, generated storage names, base name only | Tests |
| Deletes | File removal is limited to the upload directory | Test |
| Prompt injection | Input patterns, chunk sanitising, hardened prompt, model rewrites re-checked | Red team, tests |
| Data leaks | Output masking of keys and IDs, optional phone and email. **Evidence and chunk views use the same masking** | Tests |
| Errors | One safe error shape, no provider details or stack traces | Tests |
| Logs | Request metadata only, no bodies or headers | Container log scan |
| Abuse | Per-client limits on chat and upload | Tests |
| Browser hardening | CSP and related headers from nginx. CORS is off unless origins are set | Header check |
| Container | Runs as non-root `appuser` | `id` in the container |

## Limits

- **Optional shared token, not user accounts.** `RAG_API_TOKEN` protects the API with one secret. There are no users, roles or per-user data.
- **Rate limits are in memory** and per process, and use the connecting address.
- **Injection patterns cannot stop every attack,** and in the red team the hardened prompt alone already stopped all 6 indirect attacks, so the sanitizer's added value is not demonstrated.
- **Uploaded files are stored unencrypted** on the upload volume.
- **The default reports mount is too broad.** `RAG_REPORTS_HOST_DIR` defaults to the project folder, so the API container can read `.env`, database dumps and `resume.pdf` there. Point it at a folder holding only the report files.
- **The grounding check warns but does not block,** and its failure reason is not recorded.
- **Python dependencies were not scanned.** `pip-audit` is not installed. `npm audit --omit=dev` reported 0 vulnerabilities.

## Before exposing it publicly

1. Set `RAG_API_TOKEN`, and add real authentication and per-user document ownership.
2. Terminate TLS in front of nginx.
3. Set `RAG_REDACT_OUTPUT=phone,email` and remove personal documents.
4. Add provider spending limits, since visitors spend your NVIDIA quota.
5. Move rate limiting to a shared store if you run more than one instance.
6. Run `pip-audit`.

## Credentials

The scan found no exposed credentials in project files. Git has no commits or remote yet. If `.env` was ever shared elsewhere, rotate both values.
