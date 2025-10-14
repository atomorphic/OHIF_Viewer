# Repository Guidelines

## Project Structure & Module Organization
- `platform/app` hosts the viewer shell that wires configs and bundling.
- `platform/core` holds business logic; `platform/ui` and `platform/ui-next` expose component kits; `platform/i18n` stores locale packs.
- `extensions/*` deliver feature packs, `modes/*` define workflow presets, and `addOns/externals/*` ships optional integrations.
- Shared tooling lives at the repo root (`babel.config.js`, `jest.config.js`, `rsbuild.config.ts`); sample datasets sit in the `testdata` submodule and Playwright suites reside under `tests`.
- Place viewer-specific assets in `platform/app/public` and surface new public APIs through workspace `src/index.ts` barrels.

## Build, Test, and Development Commands
- `yarn dev` starts the viewer in watch mode via Lerna; set `APP_CONFIG` to switch deployment presets.
- `yarn dev:fast` spins a lightweight loop for rapid UI work; use when iterating on components.
- `yarn build` runs `lerna run build:viewer` to emit production bundles for every workspace.
- `yarn clean` or `yarn clean:deep` purge build artifacts—run before large branch rebases.
- `yarn test:unit`, `yarn test:e2e`, and `yarn test:e2e:ui` invoke Jest coverage, Playwright headless, and Playwright inspector modes respectively.

## Coding Style & Naming Conventions
- Write TypeScript or modern ES modules; prefer function components with hooks.
- Prettier enforces 2-space indentation, double quotes, and trailing commas; auto-runs via lint-staged.
- Co-locate React pieces under `src/`; name components `PascalCase.tsx`, utilities `camelCase.ts`, configs `*.config.ts`.
- Export shared symbols from package-level `index.ts` files to keep tree-shaking effective.

## Testing Guidelines
- Unit specs live alongside sources as `*.test.ts[x]`; Playwright suites reside in `tests/playwright`.
- Keep Jest’s default coverage thresholds green; add targeted cases when touching rendering or measurement logic.
- Run `yarn test:data` before `yarn test:e2e:serve` when datasets are required; refresh snapshots with `yarn test:e2e:update`.
- Tag brittle scenarios with `@skipci` only after maintainer sign-off and document the rationale in the PR.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`type(scope): summary`) as seen in history—e.g., `fix(cornerstone-dicom-rt): cache SOP handler`; launch `yarn cm` for guided prompts.
- Reference issues with `(#1234)` and reserve `[skip ci]` for automated version bumps.
- PRs need a concise summary, testing notes, linked issues, and UI screenshots or GIFs for visual changes.
- Run relevant `yarn test:*` commands before requesting review and call out any skipped checks in the description.
