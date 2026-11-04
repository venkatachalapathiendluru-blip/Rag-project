# Frontend Architecture

React 19, TypeScript, Vite, Tailwind CSS 4, React Router, TanStack Query, Axios, react-markdown with rehype-highlight, Recharts, Lucide icons and Radix primitives.

```text
frontend/src/
  app/          Routes
  layouts/      Sidebar and page frame
  services/     API client and error mapping
  types/        API types
  lib/          Formatting, theme, utilities
  components/   Shared states, MetricBars
  components/ui/ Button, Badge, ConfirmDialog, Switch, Tabs
  features/     chat, documents, conversations, overview,
                evaluation, experiments, monitoring, settings
```

`components/ui` follows the shadcn/ui pattern (Radix plus `cva`, owned in the repository), written by hand rather than generated with the shadcn CLI.

## Rules the code follows

- **Real data only.** Every number comes from the API. A missing value renders as "Not recorded", never as 0 (`lib/format.ts`).
- **No fake streaming.** The chat shows elapsed time until the validated answer arrives.
- **Citations are checked.** `features/chat/citations.ts` turns `[Chunk ID: N]` into links. Only IDs in the saved citations open evidence. Unknown IDs show as a warning.
- **Markdown is safe.** Raw HTML is not rendered, and a test covers this.
- **Evaluation versions stay apart.** `features/evaluation/labels.tsx` labels each report as original, offline annotation correction, human-approved or new.
- **Secrets stay out.** The optional token is typed by the user and kept in `sessionStorage`. Nothing secret is built into the bundle.

## Design

Recorded in `PRODUCT.md`. An operational tool with a calm neutral palette, one teal accent used for actions and selection, status colours always paired with text or an icon, IBM Plex Sans and Mono self-hosted, and light and dark themes from one set of tokens. Charts use a zero-based axis, one colour and direct labels, with the same values in a table below.

## Not implemented

- Streaming answers (the backend does not support them).
- Regenerate. Retry appears only when a request fails.
