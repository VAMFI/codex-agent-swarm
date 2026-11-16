# Codex Agent Swarm — Codex plugin preview

Swarm routes one authorized task to the smallest useful native Codex team,
records handoffs on a local board, and requires independent verification of the
current work. Version **0.2.1**. Trivial and status-only work uses zero workers.
Additional agents consume quota; savings depend on the job and are not promised.

## Use it

Ask for the outcome and constraints; the coordinator chooses a useful split:

> Use Swarm to implement [task]. Preserve existing work, assign disjoint file
> ownership, and verify the final behavior with the existing acceptance checks.

> Use Swarm to research [question] with independent source checks. Stay read-only
> and distinguish current primary evidence from assumptions.

> Use Swarm to extract these records and check schema, missing fields, and source
> fidelity. Handle it directly if a team would add no useful verification.

For adaptive models, authorize selection explicitly:

> Use Swarm with adaptive model selection for this task. Choose from this host's
> advertised models and supported reasoning settings. Keep a bounded team and
> independent verification; report limitations and actual evidence.

An explicit model/reasoning pin takes precedence. Without adaptive authority or
usable model metadata, workers inherit current settings with stated uncertainty.
An unavailable pin blocks dispatch; Swarm never silently substitutes another model.

For status:

> Use Swarm Status to inspect the existing board at [absolute path].

Status inspection never spawns, resumes, messages, migrates, or changes a board.

## What it provides

- **Swarm:** task-specific evidence policies for coding, research, writing,
  planning, extraction, visual/computer use, and high-risk investigation.
- **Useful allocation:** dependency waves, distinct author/reader slots,
  compatible idle reuse, and a separate verifier started at handoff. Default
  cap four includes retained/idle agents and the reserved verifier.
- **Local board:** ordered SQLite messages, pagination, ownership checks,
  recorded handles/task states, native-state observations, and revision gates.
- **Routing helper:** deterministic JSON plans from explicit task facts and
  live capability/model metadata. It performs no dispatch or model switching.
- **Swarm Status:** read-only progress, blockers, evidence, and available live state.

The plugin supplies skills and Python helpers. Codex's native tools execute
agents and deliver messages. Board posts do not wake idle workers. There is no
Swarm MCP server, dashboard, autonomous scheduler, background monitor, automatic
worktree provisioning, or global agent configuration change.

## Requirements and local installation

Use local Codex with native spawn/message/wait tools, Python 3.9+ with SQLite,
and a writable local scratch directory shared by workers. No separate server
or API key is needed. Normal Codex permissions, access, and quota apply.

Keep `swarm/` with its accompanying `../.agents/plugins/marketplace.json` catalog.
The public repository uses marketplace `vamfi`; the earlier local evaluation used
`swarm-local`.
From that parent marketplace root, run the supported local installation flow:

```sh
codex plugin marketplace add "$PWD"
codex plugin add swarm@vamfi
```

These commands register the local source and install/enable the same plugin
identity, `swarm@vamfi`. For updates, edit this source and refresh/reinstall
through the host's supported flow; do not edit the installed cache. Check local
CLI help for update support. Refresh the desktop client if needed, without
restarting a busy session automatically. A plugin-only ZIP needs a local
marketplace catalog pointing its `swarm` entry to `./swarm`.

Historical evaluation: version 0.2.0 was installed and enabled on the evaluation Mac. Real native
workers exercised the installed skills and helpers; see [verification](VERIFICATION.md)
and [evaluation](EVALUATION.md) for exact checks and limitations. Installation
on another host still requires its supported local flow and capabilities.

Uninstall with `codex plugin remove swarm@vamfi`. Remove the marketplace
only if unused. Preserve task boards and workspaces until reviewed.

## Review, recovery, and limits

Material producer results advance the v2 work revision. A verifier captures the
revision before review; completion records that exact revision and `finish`
rejects stale approval. The board does not monitor/hash actual files or prove
that reported checks are true. Inspect real artifacts after final edits.

Existing v0.1 boards remain readable. A deliberate `migrate` command preserves
history, upgrades the local schema, and invalidates old verifier approvals.
Migration is never silent. V2 `observe` records evidenced native-state claims;
`rebind` requires expected-handle/inactivity evidence and preserves history.
Reconcile actual files and native state before replacing any writer.

Idle or interrupted agents may retain native slots. Interruption is not permanent
termination or proof that subprocesses stopped. Same-handle follow-up can resume
intentional work when supported; changing a worker model needs a new agent on
hosts without live switching. Cancellation preserves work and reports any
remaining activity or missing visibility.

Model capability/ranking labels are documented hypotheses, not measured cost or
quality guarantees. Runtime model identity may be unobservable; distinguish a
requested model from a confirmed identity. The router uses advertised IDs and
supported efforts, with task evidence deciding adequacy. Unsupported hosts degrade
honestly. No finite local evaluation proves all models, users, or jobs succeed.

Board access is local trust, not authentication or a permission sandbox. Ownership
claims do not restrict actual filesystem access; reconcile symlink/case aliases.
Do not store secrets or unnecessary private information on the board.

## Develop and inspect

```sh
python3 -m unittest discover -s tests -v
python3 skills/swarm/scripts/board.py --help
python3 skills/swarm/scripts/route.py < /actual/run/route-input.json
```

See [routing and examples](skills/swarm/references/routing.md),
[board commands](skills/swarm/references/board.md),
[native adapter](skills/swarm/references/native-tools.md), and
[release notes](CHANGELOG.md). Primary guidance:
[model selection](https://developers.openai.com/api/docs/guides/model-selection)
and [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Live host tool schemas take precedence over examples.
