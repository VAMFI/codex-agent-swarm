# Changelog

## 0.2.1 — 2026-11-16

- Name the public project Codex Agent Swarm under VAMFI.
- Package a self-contained marketplace and public installation instructions.
- Release under the MIT license, copyright 2026 VAMFI Inc.
- Runtime, routing, and skill behavior remain identical to the tested 0.2.0 code.

## 0.2.0 — 2026-11-16

### Added

- General-purpose routing policies and a deterministic JSON planning helper for
  task dependencies, useful worker counts, role-compatible reuse, and a separate
  independent verifier. Trivial/status-only work uses zero workers.
- Opt-in adaptive model selection from live advertised IDs/efforts and explicit
  capability/adequacy hypotheses. User pins take precedence; unsupported pins
  block and missing metadata preserves inherited settings with clear limits.
- V2 material-result revisions and verifier approval tied to the revision
  captured before review. Completion rejects stale recorded verification.
- Explicit, additive v1-to-v2 board migration preserving history and requiring
  fresh verification; native-state observations and guarded handle rebinding.
- Regression coverage for routing, stale-review races, lifecycle recovery,
  malformed inputs, concurrent writes, and read-only board inspection.

### Changed

- Coordinator/worker briefs use compact context, bounded repair/escalation,
  native idle wakeup, just-in-time verification, and honest capacity accounting.
- Status remains read-only and distinguishes recorded claims from live state.
- Recovery/cancellation guidance distinguishes interrupted turns, retained native
  handles, actual writer inactivity, and subprocess visibility.

### Limits

- No automatic scheduler, native-tool implementation, runtime model identity
  guarantee, benchmark/cost savings claim, or universal task-success guarantee.
- A local board validates recorded evidence/revisions, not the truth of claims,
  filesystem changes, host authentication, or agent permissions.

## 0.1.0 — 2026-11-16

- Initial local preview: native subagent coordination skills, durable SQLite
  board, declared ownership, recorded evidence gate, and read-only status skill.
