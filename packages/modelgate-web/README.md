# modelgate-web (archived)

This is the React + Vite + Tailwind frontend built during the UAS phase
of this project. It is **archived, not actively maintained** as of the
project's pivot to a library-first focus (see `ROADMAP.md`).

**Known to be currently broken against the live server API** — Fase 5's
restructuring changed `report_service`'s response shape (tier fields
like `plan`/`grade` removed, `components` renamed, analyzer identifiers
changed from names like `"corruption"` to MGS requirement ids like
`"MGS-0001"`) and this frontend's `src/api/types.ts` /
`ReportPage.tsx` were never updated to match. Left as-is, not fixed —
active development is now entirely on `packages/modelgate-core` (the
library) and its CLI. See `CONTRIBUTING.md`.

If this is ever revived, `src/api/types.ts` and the pages under
`src/pages/` need to be brought in line with `modelgate-server`'s
current report shape (`packages/modelgate-server/report_service/services/aggregator.py`)
before it will work again.
