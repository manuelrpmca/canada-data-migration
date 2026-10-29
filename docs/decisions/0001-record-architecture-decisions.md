# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-10-29
- Milestone: M0

## Context

This is a portfolio project. A reviewer, a recruiter or an interviewer should be able to see not only what was built but why each choice was made. The owner also needs to explain every decision in an interview, so the reasoning has to be written down while it is fresh.

## Options considered

1. **No written decisions.** Fastest, but the reasoning is lost and the repository looks like a tutorial copy.
2. **One long design document.** Easy to start, hard to keep current; changes overwrite history.
3. **Short, numbered ADRs.** One file per decision, never rewritten once accepted, superseded explicitly.

## Decision

Use short, numbered ADRs in `docs/decisions/`, following the trimmed MADR template in [template.md](template.md). An ADR is accepted when the pull request that adds it is merged by the repository owner. All repository content, ADRs included, is written in English.

## Consequences

- Every tool choice in this project has a record a reader can find in one click.
- Writing an ADR adds a few minutes per decision; that cost is accepted.
- Changing direction is visible: a new ADR supersedes the old one instead of silently editing it.
