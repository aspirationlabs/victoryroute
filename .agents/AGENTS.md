# Repository Guidelines

## Project Structure & Hand-offs
- `python/game` hosts the battle engine, schemas, and protocol objects; `python/battle` layers the turn sequencing.
- `python/agents` contains strategies, prompts, and tools—create `agents/{name}` for new agent assets.
- `python/integration_tests` houses end-to-end suites with fixtures in `integration_tests/testdata`.
- `data` stores Showdown resources refreshed via `typescript/scripts/extract_showdown_data.ts`; `experimental` is reserved for spikes.

## Workflow & Planning
- Restate the goal, sketch two viable approaches, confirm direction, then publish a numbered plan with test intent.
- Keep plans current; archive lengthy or scoped-out plans in `.agents/plans/<branch>.md` and clean them up when done.
- Default `reasoning_effort` to medium, drop to low for surgical edits, raise only when multi-hop analysis is unavoidable.
- Keep tool preambles tight—state action, success criteria, fallback—and resolve ambiguity yourself while logging assumptions and residual risk in the summary.

## Build, Test & Data Sync
- Practice TDD: outline pytest cases, implement incrementally, rerun suites after substantive edits.
- Run `uv sync` once, then `uv run python python/scripts/pycheck.py` to apply Pyrefly type checks plus Ruff lint/format on touched files.
- Cover regressions with `uv run pytest python/integration_tests` (scope via `-k` when narrowing failures).
- Refresh Showdown assets through `pnpm install && pnpm run sync` (set `SHOWDOWN_DIR` when pointing at a local clone) and pull teams with `uv run python python/scripts/download_teams.py --format gen9ou`.

## Python Standards
- Activate the venv and run `pyrefly check <files>`, `ruff check .`, and `ruff format .` before proposing Python changes.
- Keep imports top-level and alphabetized, avoid `# type: ignore`, honor Ruff’s 88-character lines, and provide explicit type hints.
- Prefer dataclasses, pydantic models, UTC-aware timestamps, and dependency-injected fakes; maintain `*_test.py` absltest suites that mirror real behavior.

## TypeScript & Node Standards
- Use pnpm; run `tsc --noEmit`, `eslint . --ext .ts,.tsx,.js,.jsx`, and `prettier --check .` ahead of reviews.
- Favor `const`, avoid `any`, add targeted JSDoc, and lean on absolute imports when supported.
- Exercise changes with jest (or repo equivalent) and reuse `pnpm run …` / `ts-node` scripts for data sync jobs.

## General Development Rules
- Run language-specific lint/type suites before proposing code and prefer repo tooling over custom scripts, documenting env vars you touch.
- Keep commands atomic, avoid destructive git operations, and leave only intentional edits in the working tree.
- Capture expected outputs, manual checks, and follow-up actions inside the plan so verification stays traceable.

## Architecture & Design Patterns
- Separate interfaces from implementations in `python/game` and `python/agents`; rely on dependency injection and in-memory fakes.
- Use dataclasses, Enums, and typed registries instead of loose dicts, keeping singletons narrow and thread-safe.
- Maintain repository-style layering in `python/game/data`, isolating persistence IO from decision logic.

## Quality Gates & Review
- Run the pre-commit hook (wraps `pycheck.py`) before opening a PR; keep diffs focused and ensure every helper has a caller or test.
- Summaries should list executed commands, test evidence, open risks, and recorded assumptions.

## Code Review Checklist
- Pyrefly/Ruff and TypeScript checks pass; formatting is committed.
- Tests (pytest, jest, manual battle sims) cover new behavior and their results are noted.
- Code matches repo style, keeps error handling explicit, and avoids dead paths or stray assets.
- Docs, configs, and synced data files reflect behavioral changes.

## Commit & PR Expectations
- Write commits in the repo style: imperative summary + issue reference (e.g., `Add a base stats calculator (#35)`).
- PR descriptions include the problem, approach, verification steps, and supporting logs or screenshots.
- Tag owners for impacted areas (`python/game`, `python/agents`) and flag risks or flaky observations for reviewers.
