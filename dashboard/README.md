# CareMatch — Dashboard (Phase 3)

The coordinator-facing dashboard for CareMatch's clinical trial eligibility
review tool. This is the UI layer only, currently running on mock/local
data — wiring to the real backend (Phase 2's FastAPI service) is a
separate, upcoming step.

## Development

```sh
npm install
npm run dev
```

## Built with

- TanStack Start
- TypeScript
- React
- Tailwind CSS

## Status

- [x] New Assessment screen
- [x] Assessment Review screen (evidence display, inclusion/exclusion columns, approve/override flow)
- [x] Trial Setup screen
- [ ] Wired to the real CareMatch API (Phase 2) — currently uses mock data only
