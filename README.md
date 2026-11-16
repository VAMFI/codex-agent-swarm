# Codex Agent Swarm

A VAMFI plugin for Codex that coordinates bounded native agent teams, records
handoffs on a local board, and requires independent review of the current work.

This is a community project, not an official OpenAI product. Native subagent
tools and Python 3.9+ with SQLite are required. Extra agents consume quota.

## Install

Clone this repository and register its included marketplace:

```sh
git clone https://github.com/VAMFI/codex-agent-swarm.git
cd codex-agent-swarm
codex plugin marketplace add "$PWD"
codex plugin add swarm@vamfi
```

These commands require a Codex CLI with plugin support. Verify your host's CLI
help if unavailable. Source updates require refreshing/reinstalling the plugin.
The internal plugin ID is `swarm`; its display name is **Codex Agent Swarm**.

## Use

> Use Swarm to implement [task] with bounded workers and independent verification.

> Use Swarm with adaptive model selection for [task].

> Use Swarm Status to inspect this task's existing board.

Trivial/status-only work uses zero workers. Adaptive model choice is opt-in,
uses advertised host models, and respects explicit user pins. The local board
is a record, not a scheduler, permission sandbox, or background monitor.

See the [plugin guide](swarm/README.md), [evaluation](swarm/EVALUATION.md),
[verification](swarm/VERIFICATION.md), and [release notes](swarm/CHANGELOG.md).

## Develop

```sh
cd swarm
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Submit focused changes with relevant regression tests. Do not include local
boards, task transcripts, credentials, or private project data in reports or PRs.

## License

Copyright 2026 VAMFI Inc. Released under the [MIT License](LICENSE).
