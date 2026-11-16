# Verification — Swarm 0.2.0 — 2026-11-16

Swarm 0.2.0 was installed and enabled on this Mac with the desktop bundled
Codex CLI 0.163.0-alpha.10.2. The installed plugin ID is `swarm@swarm-local`.
Source tests, independent review, and live native-worker evidence are separate
proof classes. This preview does not establish success for every job or host.

## Reproducible source checks

From the plugin source directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -m unittest discover -s tests -v
```

- **71 tests passed** on Python 3.15.2 (18.667 seconds) and Python 3.9.6
  (13.685 seconds), independently run after final runtime/routing edits.
- Breakdown: 42 board tests, 27 routing tests, 2 package tests.
- Independent adversarial routing evaluation: 16 cases passed on each Python.
- Concurrent posting/ownership/rebind, stale-review races, migration preservation
  and rollback, legacy/schema handling, invalid input, missing board refusal,
  and read-only byte/mtime checks passed.
- A disposable mutation disabling status-only routing was caught by a failing
  regression test. Production source was unchanged by this experiment.
- Both skill frontmatters and both agent YAML files parsed with Ruby safe YAML.
  Manifest identities/presentation agree; skill supporting links resolve.
- `git diff --check` passed. No unresolved required source defect remained in
  independent review.

The original baseline had 21 tests. Initial red development runs are preserved
locally and superseded by these final passing results. Tests measure behavior
on their fixtures; they are not throughput or token-efficiency benchmarks.

## Installed and native checks

Installation used `codex plugin add swarm@swarm-local --json`; subsequent
`plugin list --marketplace swarm-local --json` reported version 0.2.0,
`installed:true`, `enabled:true`. Initial comparison matched all 20 packaged
source files; the independent reviewer compared eight execution/skill/reference
files against the reviewed fingerprints. Final release equality is checked
again after administrative evidence documents are added.

The installed routing helper reproduced a two-slot sequential extraction plan.
A reused native reader returned four records with all 20 fields correct,
including unknown/null and numeric zero; known estimates total 8 hours and the
summary is 14 words. A separate reused native verifier inspected the actual
input/output and hashes at revision 4. A later material result advanced revision
5, and installed `finish` rejected the stale review with exit 2, leaving the
board active. Fresh independent revision-5 review passed; completion then succeeded at
sequence 10. Both members are complete and verification is current. The live
installed status probe preserved database SHA-256 and modification time while
accurately reporting the earlier stale review.

Earlier live native probes exercised real startup/registration/handoffs,
independent source review and repairs, status with hostile board text, idle
handle reuse, and bounded interruption followed by same-handle continuation.
The baseline status probe left SQLite bytes unchanged and did not create
workers. The coordinator separately observed native state; worker-reported
missing status visibility is not a claim that the parent lacked that tool.

Four existing native worker handles were allocated at peak. No additional
workers were created for installed validation. Requested settings were
`gpt-6.1-sol` high for implementation, `gpt-6-astra` high for independent review,
and `gpt-6-luna` low for bounded read-only probes. The native tool did not expose
actual runtime model identity. Retaining the stronger existing verifier is
recorded as a deliberate reuse decision, not a claim that the router selected it.

## Evidence and boundaries

See [evaluation](EVALUATION.md) for task coverage, repaired defects and acceptance
mapping. Local scratch reports contain exact commands, observed outputs and
hashes; scratch boards and transcripts are excluded from the distributable ZIP.
The test suite and public evidence summaries remain in the package.

No measured token/dollar savings, optimal model ranking, universal job success,
Windows/Linux behavior, alternative host adapter execution, or actual visual/
high-risk task completion is claimed. Visual/high-risk cases were policy and
routing fixtures. No fresh-chat automatic skill-selection UI test was run.
Native lifecycle observations do not prove arbitrary subprocess cancellation.

The local board is neither authentication nor a scheduler, permission sandbox,
or file monitor. It gates recorded revisions and evidence presence; actual files
and claims still require inspection. No publication, account upload, external
service, custom dashboard, or background monitor was created.
