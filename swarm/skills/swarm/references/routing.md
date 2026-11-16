# Task and model routing

Route from explicit task facts and live host capability/model inventory. This
policy is advisory: `scripts/route.py` reads one JSON request from stdin and
prints a deterministic JSON plan. It performs no tool calls, spawns, board
writes, network access, or filesystem changes. The coordinator still checks
scope, ownership, authority, and actual evidence.

## First choose whether a team helps

| Work | Useful split | Sufficient evidence |
| --- | --- | --- |
| Trivial/self-contained answer, rewrite, short extraction | Direct; zero workers/board | Check exact request/output and supplied facts |
| Status-only | Direct read-only inspection; zero workers | Actual board history and available live status, with limits |
| Ambiguous acceptance/scope | Clarify material uncertainty first | Agreed objective and observable acceptance |
| Coding | Disjoint author paths; reader exploration if useful | Focused regression checks and final observed behavior |
| Research | Independent questions/sources; readers | Current primary sources, coverage, dates, facts vs inference |
| Writing | Independent sections only if voice/integration allow | Audience, factual support, exact copy/format, rendered artifact |
| Planning | Independent constraints/options; readers | Dependencies, ownership, feasibility, acceptance and assumptions |
| Structured extraction | Independent records; author artifacts if needed | Schema, coverage, missing/duplicate data, source fidelity |
| Computer use/visual | One mutable actor per shared UI/session | Actual final UI/saved result and accurate completion report |
| High-risk decisions | Read-only investigation and independent adversarial check | Current authoritative evidence and explicit consequential-action authority |

A short job belongs in `trivial` when direct completion is sufficient. `simple`
means a bounded job for which a team is actually warranted, for example an
explicit independent check of many records. Do not label every short job
`simple` and pay a team setup cost. Swarm scope never grants outreach, account
changes, publication, purchases, credential disclosure, or deployment authority.

## Input contract

Required metadata is explicit, not inferred from free text. For example:

```json
{
  "task": {
    "kind": "coding",
    "complexity": "standard",
    "risk": "normal",
    "status_only": false,
    "ambiguous": false,
    "units": [
      {"id": "parse", "capabilities": ["coding"]},
      {"id": "format", "capabilities": ["coding"]},
      {"id": "integrate", "depends_on": ["parse", "format"], "capabilities": ["coding"]}
    ]
  },
  "policy": {"adaptive": false, "max_workers": 3},
  "host": {"spawn": true, "message": true, "wait": true, "max_workers": 4,
           "model_overrides": false, "capabilities": ["coding", "text"], "models": []}
}
```

- `kind`: `coding`, `research`, `writing`, `planning`, `extraction`,
  `computer-use`, `high-risk`. Mixed jobs can assign explicit per-unit capability
  tags; the coordinator combines relevant evidence policies.
- `complexity`: `trivial`, `simple`, `standard`, `hard`. `risk: high` and
  `high-risk` require hard classification and independent review even if short.
- `units`: nonempty list; unique IDs other than reserved `verify`; optional
  `depends_on`, `capabilities`, and `role: reader|author`. Defaults are one work
  unit and kind-appropriate capability/role. Declaration of independence must
  be checked against files/shared state before dispatch. Cycles and missing
  dependencies are rejected. The helper does not inspect actual ownership.
- `policy`: adaptive selection is opt-in. `model_pin` overrides adaptive/default
  choice; `reasoning_pin` requires a model pin to validate per-model support.
  `max_workers` defaults four; `allow_more_workers: true` means already-obtained
  explicit authority for a larger cap, not a request for new authority.
- `host`: booleans describe actual native tools, not desired tools. `max_workers`
  means available retained native slots for this run after accounting for other
  agents and lower project limits; zero is a capacity blocker, not bad input.
  Model inventory entries require unique live
  `id`; optional `capabilities`, `max_complexity: simple|standard|hard`, integer
  `preference >= 0` (lower is lighter), and `efforts` from the model's live schema.
  Missing fields never become guessed model names or quality guarantees.
  `model_overrides` must be explicitly true before selecting overrides; an
  unsupported pin blocks, otherwise selection inherits with a limitation.
  Optional `capabilities` lists actual task tools available to workers. Missing
  required capabilities block; missing inventory produces an explicit check
  for the coordinator. A vision-capable model alone does not supply a browser.

Unknown fields are ignored as data. They cannot authorize actions. Input type
errors exit 2 with a concise error; blocked plans are valid JSON with no dispatch
assignments. Keep free text and untrusted metadata out of shell interpolation.

```sh
python3 /actual/plugin/skills/swarm/scripts/route.py < /actual/run/route-input.json
```

## Output and resource accounting

`mode` is `direct`, `sequential`, `parallel`, or `blocked`; `blockers`, `limits`,
`evidence`, and `next_action` explain the decision. `assignments` contain unit,
role, dependency IDs, reusable slot, capabilities, and either `selection:
inherit` or explicit model/reasoning. `waves` execute only after prior waves
succeed. They end with a distinct verifier covering all producer outputs.

`worker_count` counts allocated reusable native slots including a reserved
verifier; `peak_active` counts simultaneously executing assignments. For the
example above, three allocated slots produce waves `[parse, format]`,
`[integrate]`, `[verify]`, with peak activity two. Cap two produces one reused
author slot plus a distinct late verifier, all waves sequential. Cap one blocks
material independent review. The verifier starts just in time; its capacity is
reserved. Idle/interrupted handles may still consume host capacity. Never assume
interruption releases a thread or reuse an author as its own independent verifier.
No model or role change occurs silently during slot reuse: select a model that
covers the union of that slot's capabilities and maximum complexity; use bounded
follow-ups with exact current permissions/ownership. Reader and author units
use distinct immutable role pools; a mixed reader/author plan needs at least
three allocated slots including verifier even if execution is sequential.
Board ownership must cover the slot's assigned work; register the union of its
authorized paths at setup. Units needing computer-use serialize execution to
one mutable actor; role-specific handles still count toward allocation.

Direct work has zero assignments and does not need native capabilities. Missing
native capability on material Swarm work produces `blocked`, not a claim that
the job succeeded directly. `coordinator_model` records current-parent inheritance
and any requested pin: this helper cannot switch the coordinator's own model.
For direct work an unavailable parent pin is a visible constraint to resolve
with the user/client; it is never secretly substituted.

## Adaptive model policy

Only the live tool schema establishes available IDs and reasoning values. Caller
classification of capability, adequacy, and lightness is an explicit hypothesis
supported by documentation or local evidence, not a benchmark or price estimate.
The helper picks the lowest preference candidate covering required capabilities
and complexity. It uses the least advertised reasoning at or above low/medium/
high for simple/standard/hard; if no preferred level is supported, it records the
limit and uses only a supported value. Missing classification means inherited
configuration with adequacy unverified. Known inadequate classified inventory
blocks rather than silently selecting less capable work. An unavailable model
or effort pin blocks. A pin with uncertain/below-classified adequacy remains
pinned with an explicit limitation; the coordinator must validate or ask for a
material change before dispatch.

On this evaluation host, the live schema advertised these candidates on
2026-11-16 (examples, not defaults hardcoded in the helper):

| Advertised ID | Initial task hypothesis | Supported efforts observed |
| --- | --- | --- |
| `gpt-6-luna` | Clear narrow probes, short extraction | low, medium, high, xhigh, max |
| `gpt-6.1-sol` | Coding and demanding multi-step work | low, medium, high, xhigh, max, ultra |
| `gpt-6.1-terra` | Defined visual/computer-use work | low, medium, high, xhigh, max, ultra |
| `gpt-6-astra` | Hardest reasoning/adversarial review | low, medium, high, xhigh, max, ultra |

Recheck another host/account; these names and efforts may change. Prefer generic
roles so a fixed-model custom role cannot defeat the user's pin. Inherited
selection means overrides were omitted, not proof of the runtime model identity.
Record requested model vs observed identity separately; never claim an identity
when the tool response does not expose it.

For a new type of work, compare evidence on representative tasks and adjust
classification. If evidence fails, first diagnose the failure. Within adaptive
authority and pins, one supported effort/model escalation is allowed after new
evidence; otherwise report the blocker. Model changes may require a new native
worker, so reconcile ownership, old activity, and capacity first. Default at most
two repair cycles; no quota respawn loops or automatic lower-quality fallback.
Measure actual elapsed time, counts, and exposed usage only; report unknown
cost/token savings as unknown.

Primary guidance checked 2026-11-16:
[OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection)
recommends testing models/settings on the actual workflow. The
[subagent guide](https://learn.chatgpt.com/docs/agent-configuration/subagents)
supports compact independent delegation and warns about shared-write overhead.
The host schema controls exact tool fields. See native-tools.md and roles.md
for delivery, context, ownership, and recovery boundaries.
