# Frontend Testing

| Command | What runs | Latest result |
|---|---|---|
| `npx tsc -b` | Type check | Passed |
| `npx vitest run` | Component and client tests, with the API mocked | 33 passed |
| `npx oxlint` | Lint | 2 style warnings, no errors |
| `npx vite build` | Production build | Passed |
| `npm run e2e` | Real browser against a live stack | 20 of 20 passed with the mock provider |

## Browser acceptance

`e2e/acceptance.mjs` drives Chrome with `playwright-core`. `e2e/mock_provider.py` stands in for NVIDIA, so ordinary runs make no model calls. Its answers are scripted, so these runs do not measure model quality. Against a real provider, a run makes about four chat turns.

Set `E2E_EXTENDED=1` and `E2E_DB_CONTAINER=ragverify-db-1` to add six scenarios, including a database outage. The script refuses to stop a container outside the `ragverify` project.

```bash
python3 e2e/make_sample_pdf.py /tmp/northwind-handbook.pdf
E2E_URL=http://127.0.0.1:8080 E2E_PDF=/tmp/northwind-handbook.pdf E2E_SHOTS=/tmp/shots npm run e2e
```

It covers upload, grounded answers, citation evidence, refresh persistence, follow-ups, abstention, injection blocking, the saved dashboards, invalid uploads, an API outage, secret checks, phone and tablet overflow on every page, the dark theme and confirmed deletion. Optional `E2E_SECRET_CHECK` holds secrets, one per line, that must not appear in the page, config or bundles.
