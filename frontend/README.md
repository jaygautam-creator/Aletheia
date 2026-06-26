# Aletheia — Frontend

Next.js (App Router, TypeScript) dashboard for Aletheia. Phase 0 ships a static
landing page; the live, streaming agent/verification view arrives in Phase 4.

## Requirements

- Node.js 20+

## Common commands

```bash
npm install        # install dependencies
npm run dev        # dev server on http://localhost:3000
npm run build      # production build (standalone output)
npm run start      # serve the production build
npm run lint       # ESLint
npx tsc --noEmit   # type-check
```

## Configuration

Browser-exposed values use the `NEXT_PUBLIC_` prefix. The backend base URL is
read from `NEXT_PUBLIC_API_URL` (see the root `.env.example`).

## Stack

- Next.js 16 (App Router) · React 19
- TypeScript · ESLint
- Tailwind CSS v4
