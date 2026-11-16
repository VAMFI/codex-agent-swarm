# Local board CLI

Python 3.9+ standard library only. There is no MCP server, network listener,
background poller, or credential setup. SQLite transactions serialize concurrent
writes and ownership claims. Use a local disk, not a network filesystem.

Resolve these example variables to real absolute paths. Do not literally use
`/absolute/...`. Avoid common system environment variable names.

```sh
swarm_script='/absolute/plugin/skills/swarm/scripts/board.py'
swarm_db='/absolute/project/work/swarm/unique-run/board.sqlite'
python3 "$swarm_script" --db "$swarm_db" init --title 'Parser rewrite'
```

Use UTF-8 files or stdin for text. Never interpolate untrusted text into shell
commands. Write briefs and evidence through file-editing tools; the paths below
are illustrative. Omit secrets and unnecessary private details.

```sh
# Register only after native spawn returned a real handle.
python3 "$swarm_script" --db "$swarm_db" member --name parser \
  --handle /root/parser --role author --owns src/parser.py \
  --owns tests/test_parser.py --brief-file /absolute/run/parser-brief.txt

python3 "$swarm_script" --db "$swarm_db" member --name verify \
  --handle /root/verify --role verifier --brief-file /absolute/run/verify-brief.txt

python3 "$swarm_script" --db "$swarm_db" state --name parser --state running

python3 "$swarm_script" --db "$swarm_db" result --author parser --to verify \
  --text-file /absolute/run/parser-result.txt
# Next: notify verify using native messaging. Post returns delivered:false.

python3 "$swarm_script" --db "$swarm_db" read --since 0 --limit 100
python3 "$swarm_script" --db "$swarm_db" status

python3 "$swarm_script" --db "$swarm_db" state --name parser \
  --state complete --evidence-file /absolute/run/parser-result.txt

# BEFORE reviewing, read status and copy its work_revision integer as N.
# Inspect the stable final artifacts and rerun the acceptance checks.
python3 "$swarm_script" --db "$swarm_db" status
python3 "$swarm_script" --db "$swarm_db" state --name verify \
  --state complete --reviewed-revision N --evidence-file /absolute/run/verification.txt
python3 "$swarm_script" --db "$swarm_db" finish \
  --summary-file /absolute/run/final-summary.txt
```

All successful commands output JSON. Errors exit 2 and write to stderr.
`read` returns ascending sequences, `next_since`, and `has_more`. Advance only
to the last consumed sequence. A channel filter has its own cursor; `--channel`
on `post`/`read` is a tag/filter, not a subscription. No mention syntax is parsed.
The `recipient` field is metadata; one named recipient or `all` is supported.
`status.head` is diagnostic, not a read cursor.

`post` records coordination chatter. `result` uses the same arguments and
records material output with a `[result]` marker. An author, reader, or
coordinator `result` advances `status.work_revision`; a verifier report does
not. Record material changes through `result`, including source edits, revised
findings, briefs, and changed decisions. Ordinary chatter does not invalidate
verification. Neither command changes task state or delivers a native message.

States are `registered`, `running`, `waiting`, `needs_review`, `blocked`,
`complete`, `interrupted`, and `unknown`. Only the coordinator should update
these recorded task states, based on real agent results. Changing state clears
old evidence unless new evidence is supplied. `complete` requires nonblank
evidence. For authors/readers, changed state or evidence advances the work
revision; repeating identical state and evidence does not. Registration and
rebind of an author/reader also advance it. Native observations alone do not.

Verifier completion additionally requires `--reviewed-revision N`, captured
from `status` **before** inspecting the final work. Completion rejects a changed
revision, atomically, without storing the stale approval. It stores
`reviewed_revision`; `status` shows the derived `verification_current` flag.
Further material changes make that flag false, even if task state remains
`complete`. Re-review and supply the newly inspected revision. Do not simply
copy a newer revision onto old evidence. Include artifact hashes and actual
check commands/results when applicable.

No role/name authentication is enforced: every local process with access can
write the DB. Revision checks establish consistency of the recorded workflow;
they cannot detect unrecorded filesystem changes, validate a test claim, prove
that a reviewer inspected artifacts, or authenticate native observations.

`finish` requires all members complete and a separate verifier whose recorded
review matches the current revision. Every registered verifier must be current.
It checks the record, not the truth of test claims. `finish --outcome cancelled` preserves
history without a verification gate. Both make the record read-only through
this CLI. Neither interrupts an agent or subprocess. Handle lifecycle first.

Read-only commands do not create a missing DB. Initialization fails on an
existing path, including a half-initialized one; inspect it before deciding
whether to use a fresh run. The database is created with mode 0600. It is not
encrypted. Keep it and SQLite transaction sidecars out of Git. File ownership
checks reject exact and directory-prefix overlap, not symlink/case aliases,
and do not sandbox author edits. Native approval and filesystem controls apply.

New boards use schema 2. Existing schema 1 boards remain readable with `status`
and `read`; neither silently migrates them. Existing `member`, `state`, `post`
and cancellation commands remain available on active schema 1 boards. Completed
finish, `result`, `observe`, and `rebind` require an explicit upgrade:

```sh
python3 "$swarm_script" --db "$swarm_db" migrate
```

Migration preserves original messages, members, ownership, evidence and task
states. It appends an audit event and initializes revision metadata; all legacy
verifier approvals require a fresh review. It uses one transaction, including
schema changes, so failure rolls back the upgrade. Repeating it on an active
schema 2 board is a no-op. Closed boards remain read-only; start a fresh run.
Unknown or structurally incompatible schemas are rejected without overwriting.
Older helpers reject schema 2: use the new helper to inspect upgraded boards.

Recovery: read `status`, then `read --since 0` in pages, reconcile with native
agent tools and the working tree. `status.native_live` is always false: the
board never queries the host. `state` is the recorded task state; `native_state`,
`native_evidence` and `native_observed_at` are a separate historical snapshot.
The native vocabulary is `running`, `idle`, `completed`, `interrupted`,
`not_found`, `unknown`; unsupported or inconclusive results map to `unknown`.
These states do not assert tool-specific lifecycle semantics.

Reuse an idle native worker through the host's messaging/follow-up controls.
Do not rebind merely because it is idle, slow, unknown, or has stale evidence.
For a confirmed inactive worker, record the actual native observation and then
bind the same logical task to a newly spawned, real native handle:

```sh
python3 "$swarm_script" --db "$swarm_db" observe --name parser \
  --handle /root/parser --native-state interrupted \
  --evidence-file /absolute/run/native-observation.txt
# Spawn replacement using the native tool; check the returned real handle.
python3 "$swarm_script" --db "$swarm_db" rebind --name parser \
  --expected-handle /root/parser --handle /root/parser-replacement \
  --evidence-file /absolute/run/replacement-reason.txt
```

`observe` requires the current handle and nonblank evidence, and appends an
audit event. `rebind` requires the current expected handle and the latest
recorded native snapshot to be `completed`, `interrupted`, or `not_found`, with
evidence. Recording a nonterminal task state or a later worker `post`/`result`
clears an older inactive snapshot to `unknown`; obtain a fresh native
observation before rebind. Old observations remain in message history. This
clearing does not assert a live state or invalidate verification merely for
chatter. The coordinator must verify inactivity immediately before replacing;
the board cannot independently confirm it or prevent an external wakeup.
Use the host's real inactive/terminated semantics rather than guessing from a
label. If uncertain, preserve the binding and reconcile first.

Rebind preserves name, role, ownership and history; reserves both old and new
handles for the run; resets task state to `registered`; clears current
completion and native snapshot; and logs old/new handles, observation time and
reason. Old completion evidence remains in history. Concurrent rebinds against
the same expected handle allow one winner, with no ownership duplication.
It does not spawn, stop, wake, or transfer files. Keep history. No automatic
restart, quota fallback, scheduler, timer, or replay is implemented.
