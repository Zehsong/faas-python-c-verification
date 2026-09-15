# Project continuity

User instructions take precedence over this file. Read these files at the start
of a development task, then inspect the actual branch, working tree and code:

1. `docs/PROJECT_STATUS.md` — current verified state and unresolved handoff items.
2. `docs/DEVELOPMENT_PLAN.md` — proposed milestones and acceptance criteria.
3. `CHANGELOG.md` — dated changes, validation and evidence references.

## Synchronizing work

- The working branch is `codex/same-language-cache`; `main` and
  `recovery-current-work` are historical baselines as of the latest status audit.
- Record `git status --short --branch` and `git log -1 --oneline` before editing.
  Check remote changes when network access is available. Some clones fetch only
  one branch: use an explicit refspec when checking the working branch:

  ```bash
  git fetch origin refs/heads/codex/same-language-cache:refs/remotes/origin/codex/same-language-cache
  ```

- Fetching does not integrate changes. Inspect divergence and local edits before
  merging or rebasing. Do not overwrite another environment's work.
- Uncommitted cloud changes cannot be inferred from GitHub. Ask for their task,
  branch, commit or patch when they are needed; mark them unreviewed meanwhile.
- End each code/feature change with a `CHANGELOG.md` entry in the same commit.
  Include purpose, affected interfaces, actual validation, evidence location,
  remaining limitations and the next step. Identify a commit by its Git history;
  do not try to embed its own future hash in that same commit.
- Update `PROJECT_STATUS.md` when capability, branch, evidence or next priority
  changes. Update the plan when scope changes. Report the pushed commit/branch
  to the user; if work remains local, state that explicitly.

## Research and proof boundaries

- Current priority: a usable C same-language conditional-equivalence tool.
  Other same-language backends are a later research direction; do not restore
  cross-language FaaS verification as the main objective.
- Keep domain, state assumptions, observations, safety and completeness explicit.
  A counterexample to equality does not prove every input in a region differs.
- Preserve UNKNOWN for unsupported semantics, exhausted budgets or incomplete
  proofs. Native replay, mock solvers and LLM proposals are not formal proofs.
- Keep candidate discovery separate from proof and held-out expected answers.
- Use the user's modified ESBMC for their formal acceptance workflow; record the
  actual binary/version/hash. Do not silently substitute stock ESBMC.
- Treat old pass counts and user-provided logs as historical evidence. State
  whether a result was rerun, user reported, or independently inspected.
- Run checks relevant to changed behavior. Documentation-only edits need link
  and consistency checks, not a fresh full ESBMC benchmark run.
