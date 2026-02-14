# Migrate erkweb to @dagster-io/ui-components

## Context

erkweb uses 6 React components with hand-written CSS files and custom CSS variables for a dark theme. Adopting `@dagster-io/ui-components` replaces most of this custom CSS with a shared component library (Box, Button, Tabs, Tag, ListItem, SpinnerWithText, etc.) and its built-in color system. This simplifies the codebase and provides guardrails for future UI work.

**User decisions:**

- CSS modules for any remaining custom CSS (no new styled-components callsites in erkweb)
- Full migration of all 6 components in one pass
- Adopt dagster-ui Colors, drop custom CSS variables
- Dark mode only for now

## Step 1: Install dependencies

Add to `erkweb/package.json`:

**dependencies:**

- `@dagster-io/ui-components`
- `styled-components@^5.3.3` (peer dep required by library — we won't use it directly)
- `@blueprintjs/core@^5` (peer dep — needed by Tabs, Button, etc.)
- `@blueprintjs/popover2@^2` (peer dep — needed by Tooltip internals)
- `@blueprintjs/select@^5` (peer dep — needed for TypeScript types)
- `@tanstack/react-virtual@^3.0.1` (peer dep — will use for plan list virtualization)
- `react-is@^18.3.1` (peer dep for styled-components)

**devDependencies:**

- `@types/styled-components` (TypeScript support for ThemeProvider)

## Step 2: Global setup

### `erkweb/index.html`

- Remove the `<style>` block with `@font-face` declarations (Geist fonts will come from dagster-ui's `GlobalGeist`/`GlobalGeistMono`)

### `erkweb/src/client/main.tsx`

- Wrap `<App />` with `<ThemeProvider theme={theme}>` (from styled-components + dagster-ui)
- Add `<GlobalGeist />` and `<GlobalGeistMono />` siblings
- Apply dark mode class to enable dagster-ui dark theme CSS vars

### `erkweb/src/client/App.css` → `App.module.css`

- Delete `:root` CSS variables block entirely
- Convert to CSS module (`App.module.css`)
- Keep: `.app-container`, `.app`, `.review-layout`, `.main-content`, `.empty-state`, scrollbar styles
- Replace all `var(--*)` references with ui-components CSS vars (not hardcoded hex values)

## Step 3: Color strategy

**In CSS modules:** Use the CSS custom properties provided by `@dagster-io/ui-components`. The library defines CSS vars that are available when the theme is active. Reference these vars directly (e.g., `var(--dagster-color-background-default)`).

**In TSX/JS:** Use `Colors.xxx()` functions from `@dagster-io/ui-components` for inline styles and component props.

**Never hardcode hex values** — always use ui-components CSS vars or Colors functions. Replace all existing hardcoded color values with the appropriate ui-components equivalent.

| Current CSS variable | CSS var (in .module.css) | JS (in .tsx)                      |
| -------------------- | ------------------------ | --------------------------------- |
| `--bg-deepest`       | ui-components bg var     | `Colors.backgroundDefault()`      |
| `--bg-deep`          | ui-components bg var     | `Colors.backgroundLight()`        |
| `--bg-surface`       | ui-components bg var     | `Colors.backgroundLighter()`      |
| `--bg-raised`        | ui-components bg var     | `Colors.backgroundLighterHover()` |
| `--border`           | ui-components border var | `Colors.borderDefault()`          |
| `--text-primary`     | ui-components text var   | `Colors.textDefault()`            |
| `--text-secondary`   | ui-components text var   | `Colors.textLight()`              |
| `--text-muted`       | ui-components text var   | `Colors.textLighter()`            |
| `--accent-blue`      | ui-components link var   | `Colors.linkDefault()`            |
| `--accent-green`     | ui-components green var  | `Colors.accentGreen()`            |
| `--accent-purple`    | ui-components blue var   | `Colors.backgroundBlue()`         |

Note: Exact CSS var names TBD during implementation — inspect ui-components source to find the correct var names.

## Step 4: Migrate components

### 4a. ModeToggle (`components/ModeToggle.tsx`)

- **Delete** `ModeToggle.css` — fully replaced
- Replace custom tab buttons with dagster-ui `Tabs` + `Tab`
- Use `Box` for the header container with border/background props
- Logo remains a `<span>` with inline style using `Colors.linkDefault()`

### 4b. StateFilter (`components/StateFilter.tsx`)

- **Delete** `StateFilter.css` → create `StateFilter.module.css`
- Outer container: `Box` with background from Colors
- List items: use dagster-ui `ListItem` (not clickable divs)
- Selected state: use Colors for active background
- Count badges: styled with Colors values

### 4c. PlanSidebar (`components/PlanSidebar.tsx`)

- **Delete** `PlanSidebar.css` → create `PlanSidebar.module.css`
- Header: `Box` with border/background
- Count badge: dagster-ui `Tag`
- Loading: dagster-ui `SpinnerWithText` (not bare Spinner)
- Empty/error: dagster-ui `NonIdealState`
- Plan items: dagster-ui `ListItem` (not clickable divs)
- Meta tags: styled with `Colors` values

### 4d. LocalPlansList (`components/LocalPlansList.tsx`)

- **Delete** `LocalPlansList.css` → create `LocalPlansList.module.css`
- Same pattern as PlanSidebar (Box header, SpinnerWithText, NonIdealState, ListItem)

### 4e. PlanDetail (`components/PlanDetail.tsx`)

- **Delete** `PlanDetail.css` → create `PlanDetail.module.css`
- Header: `Box` with flex, border, background
- Close button: dagster-ui `Button` with icon
- PR state badges: dagster-ui `Tag` with intent (green/red/purple)
- Local/remote badges: dagster-ui `Tag`
- Action buttons: dagster-ui `Button` with `intent` prop
- Code snippets: keep as custom clickable elements in CSS module (using ui-components CSS vars for colors)
- Metadata grid: CSS module layout, labels/values use `Colors`

### 4f. PlanReviewPanel (`components/PlanReviewPanel.tsx`)

- **Delete** `PlanReviewPanel.css` → create `PlanReviewPanel.module.css`
- Header/footer: `Box` with border/background
- Copy button: dagster-ui `Button`
- Annotation Edit/Delete buttons: dagster-ui `Button`
- Comment form Save/Cancel: dagster-ui `Button`
- **Keep as CSS module** (using ui-components CSS vars for colors): line-table, gutter, line-numbers, Prism syntax tokens, annotation blocks, comment form container, selection highlighting, drag interaction styles

## Step 5: Update App.tsx

- Import `App.module.css` as `styles` instead of `./App.css`
- Replace `className="app-container"` with `className={styles.appContainer}` etc.
- Use `Colors` for any inline styles in empty-state or similar

## Files summary

**Delete (7):**

- `src/client/App.css`
- `src/client/components/ModeToggle.css`
- `src/client/components/StateFilter.css`
- `src/client/components/PlanSidebar.css`
- `src/client/components/PlanDetail.css`
- `src/client/components/LocalPlansList.css`
- `src/client/components/PlanReviewPanel.css`

**Create (6):**

- `src/client/App.module.css`
- `src/client/components/StateFilter.module.css`
- `src/client/components/PlanSidebar.module.css`
- `src/client/components/PlanDetail.module.css`
- `src/client/components/LocalPlansList.module.css`
- `src/client/components/PlanReviewPanel.module.css`

**Modify (8+):**

- `package.json` — add dependencies
- `index.html` — remove font-face block
- `src/client/main.tsx` — add ThemeProvider, GlobalGeist, GlobalGeistMono, dark mode
- `src/client/App.tsx` — CSS module import, Box usage
- `src/client/components/ModeToggle.tsx` — Tabs/Tab/Box
- `src/client/components/StateFilter.tsx` — Box, Colors, ListItem, CSS module
- `src/client/components/PlanSidebar.tsx` — Box, Tag, SpinnerWithText, NonIdealState, ListItem
- `src/client/components/PlanDetail.tsx` — Box, Button, Tag
- `src/client/components/LocalPlansList.tsx` — Box, SpinnerWithText, NonIdealState, ListItem
- `src/client/components/PlanReviewPanel.tsx` — Box, Button for header/footer/actions

## Verification

1. `yarn install` succeeds
2. `yarn dev` — app compiles with no errors
3. Dashboard mode: 3-column layout renders, plans load, state filter works, plan selection/detail works, action buttons fire correctly, code snippets copy
4. Review mode: local plans list, plan review with Prism highlighting, gutter click/drag/shift+click, annotation create/edit/delete, copy review
5. `yarn build` — production build succeeds
6. `yarn lint` and `yarn format:check` pass

## Risks

- **Blueprint CSS:** Some dagster-ui components may render Blueprint elements expecting global Blueprint CSS. If components look broken (unstyled `bp5-*` classes), add `import '@blueprintjs/core/lib/css/blueprint.css'` to `main.tsx`
- **styled-components + Vite:** Should work fine for client-only SPA. If HMR issues arise with styled-components, add `vite-plugin-styled-components`
