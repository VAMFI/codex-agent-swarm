# Evaluation — 2026-11-16

This evaluation asked whether Swarm can make general Codex work more useful
through bounded delegation, task-aware choices and independent review. The
observed result is a tested local preview, with explicit limits rather than a
claim of universal model quality or guaranteed savings.

## Acceptance coverage

| Requirement | Evidence |
| --- | --- |
| Installed baseline/native coordination | Real authors, independent reviewer, START/registration, board/native handoffs and corrective feedback |
| General task handling | Seven job categories in routing tests and independent probes; direct trivial/status/ambiguous paths |
| Efficient allocation | Dependency waves, retained-slot accounting, distinct reader/author roles, reserved verifier, single shared UI actor, real idle reuse |
| Model selection | Advertised-ID/effort checks, explicit pin precedence, opt-in adaptation, honest inheritance/missing-capability blockers; requested models distinguished from identity |
| Lifecycle | Regression checks for ownership, review races, stale inactivity, migration and rebind; native interruption and same-handle resume |
| Read-only status | CLI byte/mtime tests; real status probe with hostile data; installed stale-review status probe |
| Adversarial review | Independent verifier found defects, authors fixed them, verifier reran final tests and separate probes; mutation test detects bypass |
| Compatibility | Explicit transactional v1 migration; old boards readable; no silent migration; v1 baseline retained |
| Delivery | Version 0.2.0 source, local install enabled, installed helper execution/equality, release archive and verification receipt |

## What changed because of evidence

1. Baseline completion accepted old verifier approval after producer work
   reopened. V2 binds approval to the revision captured before review and
   atomically rejects changes during or after that review.
2. A historical inactive native snapshot survived newer task activity and could
   permit rebinding. Later worker activity/nonterminal state now clears that
   snapshot; fresh evidenced observation is required before replacement.
3. Routing could reuse one slot for both reader and author roles. Separate role
   pools now preserve read-only responsibility and include them in capacity.
4. Exhausted host capacity zero was treated as malformed input. It now returns
   a valid blocked plan with no dispatch assignments.
5. Container-valued task types produced an unhelpful path. Input validation now
   returns a concise CLI error. Unsupported pins/tools never silently substitute.

## Task coverage and honest limits

| Job | Evidence class |
| --- | --- |
| Coding | Live parallel implementation and independent regression/review cycle; 71 final source tests on two Python versions |
| Research | Source-grounded routing documentation and independent checks; category policy/fixture evaluation, not a broad research benchmark |
| Writing | Actual bounded factual summaries and release documentation review; no arbitrary long-form editorial benchmark |
| Planning | Actual implementation ownership/dependencies; deterministic dependency/capacity/pin scenarios |
| Extraction | Live three-record baseline and four-record installed output; every field, unknowns, zero, sum and summary checked |
| Computer use/visual | Model/tool availability and one-actor routing fixtures; no rendered UI job completed in this evaluation |
| High risk | Authority/review/capability policies and fixtures; no consequential external action performed |
| Status/recovery | Native read-only reports, reuse, interruption/resumption, observed vs recorded state; no arbitrary subprocess-stop guarantee |

The router uses caller-supplied capability/complexity/preference hypotheses.
A suitable-looking plan is not proof of model adequacy. Test actual work,
preserve user pins, and stop or escalate within authority when evidence fails.
No price, token, latency, or productivity improvement percentage was measured.
Short tasks stay direct; independent review is reserved for work that benefits
from it or explicitly requests it.

## Local provenance

The v1 evaluation board and installed-v2 board live in this workspace's
`work/swarm/evaluation-20261116` and `work/swarm/installed-v020` directories.
Independent scratch evidence is in `work/verify` beneath the plugin source.
These are local run records, intentionally excluded from the package. Exact
portable regression checks and results are in [VERIFICATION.md](VERIFICATION.md).
The distributable contains no task SQLite databases or private transcripts.
