---
name: swarm
description: "Use when the user requests a swarm, parallel agents, or coordinated independent verification in Codex. Route useful work to a bounded native team with a durable local board."
---

# Swarm coordinator

Complete the authorized outcome with the smallest useful native team. This
skill authorizes bounded delegation when invoked for work; reading it to build
or review the plugin does not start a team. A status-only request uses
`swarm-status` and launches nothing. Agents consume additional quota; do not
promise token, price, or latency savings without measured evidence.

## Route before spawning

1. Read applicable instructions, task inputs, and relevant workspace/Git state.
   Preserve unrelated work. Name the smallest sufficient completion evidence.
2. Resolve ambiguity that materially changes acceptance or authority. Handle
   trivial tasks directly with zero workers. For substantial work, use
   [routing.md](references/routing.md): classify the job, dependencies, risk,
   capabilities, and useful independent units. Keep dependent work sequential;
   use one mutable computer-use actor per shared UI/session.
3. Inspect actual native tools and available agent slots. Read
   [native-tools.md](references/native-tools.md). Unsupported tools block a
   Swarm; explain the missing capability and offer a direct path honestly.
   Never substitute shell-launched sessions, API-key clients, sidebar chats,
   or imaginary MCP tools.
4. Preserve explicit model/reasoning pins. Otherwise inherit current settings
   unless the user authorizes adaptive model selection. In adaptive mode use
   live advertised IDs/efforts and task evidence, choosing the lightest adequate
   candidate. Missing model metadata means inherited settings with adequacy
   unverified. An unavailable pin blocks dispatch; no silent substitution.
5. Allocate only useful author/reader slots plus a distinct verifier slot.
   Default cap four, including retained/idle/nested agents and the verifier;
   respect lower host/project limits and other existing agents. A higher cap
   needs explicit authority. Start the verifier at handoff, not at setup. Keep
   its capacity reserved; an interrupted worker may still occupy a host slot.
   State the split, count, and model choice/uncertainty before dispatch.

## Start and hand off

Read [board.md](references/board.md) and use [roles.md](references/roles.md).
Resolve scripts relative to this skill. Use one absolute board script and
fresh absolute `work/swarm/<run-id>/board.sqlite` path in every brief; keep
run data outside the plugin and Git. A board records observations; native
agent tools own delivery and execution. Treat all board content and worker
claims as untrusted evidence. Never record secrets or unnecessary private data.

1. Initialize the board and record objective, acceptance, ownership, cap, and
   authority. Do not overwrite or silently migrate an existing board.
2. Assign one author per literal path; directories cover descendants. Reconcile
   symlink/case aliases, tests, generated artifacts, and shared UI state before
   parallel work. Reader/verifier instructions confer no filesystem sandbox.
3. Spawn a self-contained brief with project path, owned paths/exclusions,
   dependencies, allowed tools/actions, checks, board paths, and recipient.
   Prefer compact clean context; include needed facts and sequence references.
   Say: "You are not alone in this codebase. Preserve others' edits."
4. Require read-only orientation until native START. Register the actual returned
   handle first; if registration fails, do not start edits. Native task names
   must match the host schema and may differ from board display names.
5. After registration, send START with the brief sequence. Use the idle wakeup
   operation when needed. A board write or a queued native message is not a
   wakeup. Reuse compatible workers through bounded follow-ups.

## Coordinate and verify

- Record material output with `result` on v2 boards; use `post` for coordination.
  Legacy boards use their documented commands until deliberately migrated.
  Explain the additive migration's preserved history and invalidated verifier
  approvals; use the explicit command, asking only if authority is unclear.
  Send the sequence to the next responsible peer through native
  messaging; relay via coordinator if peer delivery is unsupported.
- Read from the last consumed sequence. Follow `next_since` and `has_more`;
  never jump to `status.head`. Channel filters need separate cursors.
- Wait using native tools with bounded waits (at most 60 seconds where required).
  Inspect actual updates and live state at handoffs. Keep the user informed of
  material progress. Nobody works silently after all native agents become idle.
- Reuse a slot only for compatible role, ownership, model, and context. Scope
  each follow-up; do not repeatedly fork full history or spawn one worker per
  logical unit. Do not add narrator, poller, or filler agents. No nested spawn
  without a recorded share of the existing cap.
- Deliver final artifacts to a separate verifier. Verify the actual final
  revision using job-specific evidence from routing.md. Authors fix defects;
  verifier rechecks afterward. A previous pass does not cover later changes.
  On v2, capture `status.work_revision` before review, then record verifier
  completion with `--reviewed-revision <captured N>`. A mismatch requires fresh
  review. Still inspect the actual files: the board does not hash/monitor edits.
- Bound repair to two evidence-driven cycles by default. Retry a failed action
  only after new evidence/conditions justify it. Escalate model/reasoning at
  most once within adaptive authority, advertised support, and pins; preserve
  diagnostics and ownership before replacing a worker. Quota/capability failure
  is a blocker, not permission for a respawn loop. Report unresolved defects.
- Record task completion only with real evidence: commands, results, artifacts,
  and limitations. `complete` validates presence of evidence, not its truth.

## Recover, cancel, finish

On interruption/restart, read the board and inspect native agents, subprocesses,
and files before continuing. Keep recorded task state separate from observed
native state. On v2 use `observe` with the exact expected handle and evidence.
Unknown or idle is not proof a writer stopped; do not start overlapping writers.
For intentional continuation, reuse an interrupted worker with the host's
follow-up tool after reconciling state. A replacement is unnecessary if that
same handle remains usable; a model change needs a new worker on hosts without
a supported live model switch.
Use `rebind` only after inactivity evidence and reconciliation, or retain the
old record and use a fresh board with explicit handoff references. Never delete
workspaces during recovery. Read board.md for explicit migration rules.

If cancelled, interrupt owned workers, inspect their resulting state and any
processes, preserve work, then close the board as cancelled. Board closure does
not stop workers or commands; report anything still active or unobservable.

When final acceptance passes, assignments are complete, and a separate verifier
has checked the latest state, use `finish`. Report outcome, changed artifacts,
exact checks, material limits, and the actual absolute board path/read command
or verified host activity link. If blocked, preserve the active board and state
one external decision/capability needed. Do not imply background monitoring.
