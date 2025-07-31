# Web Frontend Service

Progressive Web App (PWA) frontend for the Diet Issue Tracker platform.

## Overview

This service provides:

- Mobile-first responsive design
- Accessibility-focused UI with ARIA support
- Real-time issue tracking and visualization
- Semantic search interface
- Personalized recommendations
- Offline capability through PWA features

## Tech Stack

- Next.js 14 with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- React Query for data fetching
- Zustand for state management
- Chart.js for data visualization

## Key Features

### Issue Navigation

- 3-layer hierarchical category browsing
- Drill-down navigation (L1 → L2 → Bills)
- Category-based filtering and search
- Policy area statistics and trends

### Intelligent Features

- LLM-generated issue insights
- Bill impact visualization
- Semantic search across content
- Personalized recommendations
- Real-time political agenda tracking

### Accessibility

- WCAG 2.1 AA compliance
- Furigana toggle for kanji
- Keyboard navigation
- Screen reader optimization
- Color-blind friendly palette (#27AE60/#C0392B/#F1C40F)

## Directory Structure

```
web-frontend/
├── src/
│   ├── app/            # Next.js app router pages
│   ├── components/     # React components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utility functions
│   ├── services/       # API client services
│   ├── store/          # State management
│   └── types/          # TypeScript definitions
├── public/             # Static assets
├── tests/
│   ├── unit/           # Component tests
│   ├── integration/    # Integration tests
│   └── e2e/            # End-to-end tests
└── scripts/            # Build and deployment scripts
```

## Performance Goals

- Mobile load time ≤200ms
- Lighthouse scores >90
- First Contentful Paint <1.5s
- Time to Interactive <3.5s

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Run tests
npm test

# Run E2E tests
npm run test:e2e

# Run linting
npm run lint

# Type checking
npm run type-check
```

## Environment Variables

Create `.env.development` for local development:

```bash
# Copy example file
cp .env.example .env.development

# Environment variables
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080  # API Gateway URL
NEXT_PUBLIC_SITE_NAME=Diet Issue Tracker
NEXT_PUBLIC_SITE_DESCRIPTION=国会の課題をトラッキングするプラットフォーム
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_DEBUG=true
```

For production, create `.env.production` with appropriate values.

## Testing

- Unit tests: Jest + React Testing Library
- E2E tests: Playwright
- Accessibility: Axe-core integration

## Deployment

The frontend is containerized and deployed to Cloud Run:

```bash
# Build Docker image
docker build -t web-frontend .

# Run locally
docker run -p 3000:3000 web-frontend
```

## Monitoring

- Web Vitals tracking
- Error boundary implementation
- Analytics integration (privacy-compliant)
