# Compass Admin Panel (React)

Modern React-based admin panel for managing Compass Bot organizations, tokens, and analytics.

## Tech Stack

- **React 18.3** - UI library
- **TypeScript 5.7** - Type safety
- **Vite 6.0** - Build tool & dev server
- **TanStack Query 5.60** - Data fetching & caching
- **React Router 6.28** - Client-side routing
- **Tailwind CSS 3.4** - Styling

## Development

### Prerequisites

- Node.js 18+ and npm
- Python backend running on `localhost:8080` (for API requests)

### Setup

```bash
cd packages/admin-ui
npm install
```

### Run Development Server

```bash
npm run dev
```

Opens on `http://localhost:3001` with hot module replacement.

API requests are proxied to `localhost:8080` via Vite's proxy configuration.

### Build for Production

```bash
npm run build
```

Output goes to `dist/` directory. The Python backend (`compass-admin-panel`) automatically serves this build when available.

## Project Structure

```
src/
├── main.tsx              # Entry point
├── App.tsx               # Router setup
├── index.css             # Global styles with Tailwind
├── pages/                # Page components
│   ├── OrganizationsPage.tsx
│   ├── TokensPage.tsx
│   ├── OnboardingPage.tsx
│   └── AnalyticsPage.tsx
├── components/           # Reusable UI components
│   ├── PlanBadge.tsx
│   ├── Pagination.tsx
│   ├── LoadingSpinner.tsx
│   ├── ErrorMessage.tsx
│   ├── CopyButton.tsx
│   ├── ActionsDropdown.tsx
│   ├── OrganizationTable.tsx
│   ├── TokenTable.tsx
│   ├── TokenForm.tsx
│   ├── OnboardingTable.tsx
│   └── AnalyticsEventTable.tsx
├── hooks/                # React Query hooks
│   ├── useOrganizations.ts
│   ├── useTokens.ts
│   ├── useOnboarding.ts
│   └── useAnalytics.ts
├── api/                  # API client layer
│   ├── client.ts
│   ├── organizations.ts
│   ├── tokens.ts
│   ├── onboarding.ts
│   └── analytics.ts
├── types/                # TypeScript types
│   ├── organization.ts
│   ├── token.ts
│   ├── onboarding.ts
│   └── analytics.ts
├── layouts/              # Layout components
│   └── AdminLayout.tsx
└── utils/                # Utility functions
    └── format.ts
```

## Features

### Organizations Page

- Paginated table with sortable columns
- Plan type badges (Free, Starter, Team, Design Partner)
- Usage tracking with over-limit highlighting
- Stripe customer/subscription links
- Actions dropdown:
  - View Analytics
  - Convert to different plans
- Real-time plan type loading

### Tokens Page

- Create invite tokens (UUID or custom)
- Multi-use vs single-use toggle
- Bonus answers configuration
- Click-to-copy onboarding links
- Token status tracking

### Onboarding Page

- Organization setup progress tracking
- Initial setup steps
- Usage milestones
- Error event tracking
- Lazy-loaded analytics details

### Analytics Page

- Organization-specific event viewer
- Expandable event rows with metadata
- JSON metadata formatting
- Pagination support

## API Endpoints

All API endpoints are prefixed with `/api/`:

- `GET /api/organizations?page=1&limit=25`
- `GET /api/plan-types?org_ids=1,2,3`
- `POST /api/convert-to-{plan}` (design-partner, free, starter, team)
- `GET /api/tokens`
- `POST /api/tokens`
- `GET /api/onboarding?limit=100`
- `GET /api/onboarding/{org_id}/details`
- `GET /api/analytics?organization_id={id}&page=1&limit=50`

## Deployment

The React app is automatically served by the Python backend when built:

1. Build the React app: `npm run build`
2. The Python backend detects `admin-ui/dist/` and serves it
3. Falls back to legacy HTML pages if React build not found

No separate deployment needed!

## Code Style

- Prettier for formatting (see `.prettierrc.json`)
- Run `npm run format` to format code
- Run `npm run lint` to check formatting

## Testing

Use the Python backend's test infrastructure to test API integration.

For E2E testing, consider adding Playwright tests (already a dependency).
