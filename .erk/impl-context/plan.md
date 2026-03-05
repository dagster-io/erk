# Plan: Create Astro/Starlight v2 Docs Site for Erk

## Context

Erk's current docs use MkDocs Material, deployed to `dagster-io.github.io/erk/` via `mkdocs gh-deploy`. The moat project (`/Users/schrockn/code/githubs/moat`) has excellent documentation conventions — a comprehensive style guide, four-section Diátaxis taxonomy with litmus tests, `NN-slug.md` file naming, and structured frontmatter. The goal is to create a v2 docs site using Astro + Starlight that adopts moat's quality conventions, scaffolded with example pages. The existing MkDocs site continues working in parallel.

## Deployment Constraint

GitHub Pages serves one site per repo. The current MkDocs site uses `mkdocs gh-deploy --force` which pushes to the `gh-pages` branch at the root. Two options for coexistence:

1. **Subdirectory approach**: Deploy docs-v2 into a `v2/` subdirectory of `gh-pages`, accessible at `dagster-io.github.io/erk/v2/`
2. **Manual-only for now**: Create the workflow as `workflow_dispatch` only (manual trigger), don't auto-deploy on push

**Recommendation**: Option 2 — keep it manual-trigger only until you're ready to switch over or decide on a URL scheme. The infrastructure is in place to deploy whenever you want.

## Steps

### 1. Scaffold Starlight project in `docs-v2/`

```
docs-v2/
├── astro.config.mjs
├── package.json
├── tsconfig.json
├── public/
│   └── favicon.svg
└── src/
    ├── content.config.ts
    └── content/
        └── docs/
            ├── index.mdx              # Landing page (splash template)
            ├── getting-started/
            │   └── 01-introduction.md
            ├── concepts/
            │   └── 01-plan-oriented-engineering.md
            ├── guides/
            │   └── 01-local-workflow.md
            └── reference/
                └── 01-cli.md
```

### 2. Create `docs-v2/package.json`

Dependencies: `astro`, `@astrojs/starlight`. Scripts: `dev`, `build`, `preview`.

### 3. Create `docs-v2/astro.config.mjs`

```js
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://dagster-io.github.io',
  base: '/erk',
  integrations: [
    starlight({
      title: 'erk',
      social: { github: 'https://github.com/dagster-io/erk' },
      sidebar: [
        { label: 'Getting Started', autogenerate: { directory: 'getting-started' } },
        { label: 'Concepts', autogenerate: { directory: 'concepts' } },
        { label: 'Guides', autogenerate: { directory: 'guides' } },
        { label: 'Reference', autogenerate: { directory: 'reference' } },
      ],
    }),
  ],
});
```

Sidebar uses `autogenerate` — Starlight sorts by `sidebar.order` frontmatter, so the `NN-` prefix convention combined with frontmatter order values controls sequencing.

### 4. Create `docs-v2/tsconfig.json` and `docs-v2/src/content.config.ts`

Standard Starlight boilerplate — extends Astro strict config, imports Starlight's content collection definitions.

### 5. Create example pages with moat-style frontmatter

Each page uses Starlight-compatible frontmatter adapted from moat's schema:

```yaml
---
title: "Page Title"
description: "One sentence for SEO and previews."
sidebar:
  order: 1
  label: "Nav Title"  # optional, like moat's navTitle
---
```

Four example pages (one per section) with real erk content sketched out:

- **getting-started/01-introduction.md** — What erk is, core workflow, who it's for. Content drawn from `docs/index.md` and `docs/TAO.md`.
- **concepts/01-plan-oriented-engineering.md** — The philosophy. Content drawn from `docs/TAO.md` and `docs/topics/plan-oriented-engineering.md`.
- **guides/01-local-workflow.md** — Plan → implement → ship locally. Content drawn from `docs/howto/local-workflow.md`.
- **reference/01-cli.md** — CLI command reference scaffold. Content drawn from `docs/ref/commands.md`.

### 6. Create `docs-v2/src/content/docs/index.mdx`

Landing page using Starlight's `splash` template with a hero section. Brief intro to erk with links into the four sections.

### 7. Create `docs-v2/STYLE-GUIDE.md`

Adapt moat's style guide (`/Users/schrockn/code/githubs/moat/docs/STYLE-GUIDE.md`) for erk:

- Same voice/tone rules (objective, factual, direct, concise, precise, practical)
- Same banned words list (revolutionary, seamless, powerful, elegant, etc.)
- Same formatting conventions (headings, code blocks, admonitions, tables)
- Erk-specific terminology table (plan, worktree, implement, land, dispatch, etc.)
- Erk-specific section litmus tests adapted from moat's four-section definitions

### 8. Create GitHub Actions workflow

Create `.github/workflows/docs-v2.yml`:

- `workflow_dispatch` only (manual trigger) — no auto-deploy on push yet
- Installs Node 20, runs `npm ci` and `astro build` in `docs-v2/`
- Uses `actions/upload-pages-artifact` + `actions/deploy-pages` pattern
- Separate from existing `docs.yml` workflow

### 9. Add Makefile targets

```makefile
docs-v2-build:
	cd docs-v2 && npm run build

docs-v2-serve:
	cd docs-v2 && npm run dev
```

### 10. Update `.gitignore`

Add `docs-v2/node_modules/` and `docs-v2/dist/` entries.

## Files to Create

| File | Purpose |
|------|---------|
| `docs-v2/package.json` | Astro + Starlight dependencies |
| `docs-v2/astro.config.mjs` | Starlight config with sidebar |
| `docs-v2/tsconfig.json` | TypeScript config |
| `docs-v2/public/favicon.svg` | Favicon placeholder |
| `docs-v2/src/content.config.ts` | Starlight content collection |
| `docs-v2/src/content/docs/index.mdx` | Landing/splash page |
| `docs-v2/src/content/docs/getting-started/01-introduction.md` | Example: getting started |
| `docs-v2/src/content/docs/concepts/01-plan-oriented-engineering.md` | Example: concept page |
| `docs-v2/src/content/docs/guides/01-local-workflow.md` | Example: guide page |
| `docs-v2/src/content/docs/reference/01-cli.md` | Example: reference page |
| `docs-v2/STYLE-GUIDE.md` | Adapted from moat's style guide |
| `.github/workflows/docs-v2.yml` | GitHub Pages deployment (manual trigger) |

## Files to Modify

| File | Change |
|------|--------|
| `Makefile` | Add `docs-v2-build` and `docs-v2-serve` targets |
| `.gitignore` | Add `docs-v2/node_modules/` and `docs-v2/dist/` |

## Key References

- **Moat style guide**: `/Users/schrockn/code/githubs/moat/docs/STYLE-GUIDE.md`
- **Moat README**: `/Users/schrockn/code/githubs/moat/docs/README.md`
- **Existing erk docs**: `docs/index.md`, `docs/TAO.md`, `docs/howto/local-workflow.md`
- **Existing deploy workflow**: `.github/workflows/docs.yml`
- **Existing Makefile**: `Makefile` (lines 157-166 for current docs targets)

## Verification

1. `cd docs-v2 && npm install && npm run dev` — site loads at localhost with all 4 sections in sidebar
2. `npm run build` — builds without errors
3. Each example page renders with correct title, description, and sidebar ordering
4. Landing page uses splash template with hero
5. `make docs-serve` still works (MkDocs unchanged)
6. Style guide is present and adapted for erk terminology
