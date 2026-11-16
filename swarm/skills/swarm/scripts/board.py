#!/usr/bin/env python3
"""Local swarm record. Does not spawn, signal, authenticate, or supervise agents."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys


SCHEMA = """
CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
 title TEXT NOT NULL, outcome TEXT NOT NULL, work_revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE members (name TEXT PRIMARY KEY, handle TEXT NOT NULL UNIQUE,
 role TEXT NOT NULL, owns TEXT NOT NULL, state TEXT NOT NULL,
 evidence TEXT NOT NULL, updated_at TEXT NOT NULL,
 reviewed_revision INTEGER, native_state TEXT NOT NULL DEFAULT 'unknown',
 native_evidence TEXT NOT NULL DEFAULT '', native_observed_at TEXT NOT NULL DEFAULT '');
CREATE TABLE messages (seq INTEGER PRIMARY KEY AUTOINCREMENT,
 at TEXT NOT NULL, author TEXT NOT NULL, recipient TEXT NOT NULL,
 channel TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE bindings (handle TEXT PRIMARY KEY, member TEXT NOT NULL,
 at TEXT NOT NULL);
"""
STATES = ('registered', 'running', 'waiting', 'needs_review', 'blocked',
          'complete', 'interrupted', 'unknown')
NATIVE_STATES = ('running', 'idle', 'completed', 'interrupted', 'not_found', 'unknown')
INACTIVE_STATES = ('completed', 'interrupted', 'not_found')
V1_COLUMNS = {
    'meta': {'id', 'version', 'title', 'outcome'},
    'members': {'name', 'handle', 'role', 'owns', 'state', 'evidence', 'updated_at'},
    'messages': {'seq', 'at', 'author', 'recipient', 'channel', 'text'},
}
V2_COLUMNS = {
    **V1_COLUMNS,
    'meta': V1_COLUMNS['meta'] | {'work_revision'},
    'members': V1_COLUMNS['members'] | {
        'reviewed_revision', 'native_state', 'native_evidence', 'native_observed_at'},
    'bindings': {'handle', 'member', 'at'},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def nonblank(value, label, maximum=32000):
    if not value.strip() or len(value) > maximum:
        raise ValueError(f'{label} must contain 1..{maximum} characters')
    return value


def name(value):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}', value):
        raise ValueError('names must use lowercase letters, digits and hyphens')
    return value


def content(filename):
    if filename == '-':
        value = sys.stdin.read(32001)
    else:
        with open(filename, encoding='utf-8') as stream:
            value = stream.read(32001)
    return nonblank(value, 'text')


def append(db, author, recipient, text, channel='main'):
    return db.execute(
        'INSERT INTO messages(at,author,recipient,channel,text) VALUES(?,?,?,?,?)',
        (now(), author, recipient, channel, text)).lastrowid


def initialize(path, title):
    nonblank(title, 'title', 200)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental reset of a previous run.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(SCHEMA)
        db.execute('INSERT INTO meta(id,version,title,outcome) VALUES(1,2,?,?)',
                   (title, 'active'))
        seq = append(db, 'coordinator', 'all', f'[start] {title}')
    return {'db': str(path), 'seq': seq}


def ownership(paths):
    result = []
    for path in paths:
        parts = path.split('/')
        if (PurePosixPath(path).is_absolute() or
                any(p in ('', '.', '..') for p in parts) or
                any(c in path for c in '*?[]\\\n\r')):
            raise ValueError('ownership must be literal relative paths, without . or ..')
        result.append(path)
    return sorted(set(result))


def members(db):
    result = [dict(row) for row in db.execute('SELECT * FROM members ORDER BY name')]
    for member in result:
        member['owns'] = json.loads(member['owns'])
    return result


def metadata(db):
    actual_meta = {row['name'] for row in db.execute('PRAGMA table_info(meta)')}
    if not V1_COLUMNS['meta'] <= actual_meta:
        raise ValueError('invalid board schema: meta; do not overwrite this file')
    rows = db.execute('SELECT * FROM meta').fetchall()
    if len(rows) != 1 or rows[0]['id'] != 1 or rows[0]['version'] not in (1, 2):
        raise ValueError('unsupported board schema; do not overwrite this file')
    meta = rows[0]
    columns = V1_COLUMNS if meta['version'] == 1 else V2_COLUMNS
    for table, expected in columns.items():
        actual = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
        if actual != expected:
            raise ValueError(f'invalid board schema: {table}; do not overwrite this file')
    if (meta['outcome'] not in ('active', 'completed', 'cancelled') or
            (meta['version'] == 2 and
             (not isinstance(meta['work_revision'], int) or meta['work_revision'] < 0))):
        raise ValueError('invalid board metadata; do not overwrite this file')
    return meta


def migrate(db, meta):
    if meta['version'] == 2:
        return {'version': 2, 'migrated': False}
    if meta['outcome'] != 'active':
        raise ValueError('board is closed; history is read-only, start a new run')
    # Individual transactional DDL statements: executescript would commit early.
    db.execute('ALTER TABLE meta ADD COLUMN work_revision INTEGER NOT NULL DEFAULT 0')
    db.execute('ALTER TABLE members ADD COLUMN reviewed_revision INTEGER')
    db.execute("ALTER TABLE members ADD COLUMN native_state TEXT NOT NULL DEFAULT 'unknown'")
    db.execute("ALTER TABLE members ADD COLUMN native_evidence TEXT NOT NULL DEFAULT ''")
    db.execute("ALTER TABLE members ADD COLUMN native_observed_at TEXT NOT NULL DEFAULT ''")
    db.execute('CREATE TABLE bindings (handle TEXT PRIMARY KEY, member TEXT NOT NULL, at TEXT NOT NULL)')
    db.execute('INSERT INTO bindings SELECT handle,name,updated_at FROM members')
    db.execute('UPDATE meta SET version=2 WHERE id=1')
    seq = append(db, 'coordinator', 'all',
                 '[migrate] Schema 1 -> 2; legacy verifier approvals require a fresh review.')
    return {'version': 2, 'migrated': True, 'seq': seq}


def advance_work(db):
    db.execute('UPDATE meta SET work_revision=work_revision+1 WHERE id=1')


def get_member(db, member_name):
    member = db.execute('SELECT * FROM members WHERE name=?', (member_name,)).fetchone()
    if not member:
        raise ValueError('unknown member')
    return member


def reserve_handle(db, handle, member_name):
    if db.execute('SELECT 1 FROM bindings WHERE handle=?', (handle,)).fetchone():
        raise ValueError('native handle already used in this run; use a fresh binding')
    db.execute('INSERT INTO bindings VALUES(?,?,?)', (handle, member_name, now()))


def clear_inactive_observation(db, member_name):
    # Later recorded activity contradicts an older inactivity snapshot. Clear it
    # without inventing a new live state; the original remains in message history.
    db.execute("UPDATE members SET native_state='unknown',native_evidence='',"
               "native_observed_at='' WHERE name=? AND native_state IN "
               "('completed','interrupted','not_found')", (member_name,))


def run(db, args):
    meta = metadata(db)
    command = args.command
    if command == 'status':
        registered = members(db)
        if meta['version'] == 2:
            for member in registered:
                if member['role'] == 'verifier':
                    member['verification_current'] = (member['state'] == 'complete' and
                        member['reviewed_revision'] == meta['work_revision'])
        return {**dict(meta), 'members': registered, 'native_live': False,
                'head': db.execute('SELECT COALESCE(MAX(seq),0) FROM messages').fetchone()[0],
                'notice': 'Recorded state only; native observations are historical claims, not live status.'}
    if command == 'read':
        if args.since < 0 or not 1 <= args.limit <= 500:
            raise ValueError('since must be >= 0; limit must be 1..500')
        query, params = 'SELECT * FROM messages WHERE seq > ?', [args.since]
        if args.channel:
            query += ' AND channel = ?'
            params.append(name(args.channel))
        rows = [dict(row) for row in db.execute(
            query + ' ORDER BY seq LIMIT ?', params + [args.limit + 1])]
        visible = rows[:args.limit]
        return {'messages': visible, 'has_more': len(rows) > args.limit,
                'next_since': visible[-1]['seq'] if visible else args.since}
    if meta['outcome'] != 'active':
        raise ValueError('board is closed; history is read-only, start a new run')
    if command == 'migrate':
        return migrate(db, meta)
    if meta['version'] == 1 and (command in ('observe', 'rebind', 'result') or
            (command == 'finish' and args.outcome == 'completed')):
        raise ValueError('schema 1 cannot verify current work; run explicit migrate first')
    if command == 'member':
        name(args.name)
        if args.name in ('all', 'coordinator'):
            raise ValueError('reserved member name')
        nonblank(args.handle, 'native handle', 300)
        owns = ownership(args.owns)
        if args.role != 'author' and owns:
            raise ValueError('readers and verifiers cannot claim write ownership')
        if args.role == 'author' and not owns:
            raise ValueError('authors require explicit ownership')
        for member in members(db):
            for left in owns:
                for right in member['owns']:
                    if left == right or left.startswith(right + '/') or right.startswith(left + '/'):
                        raise ValueError(f'ownership overlaps member {member["name"]}: {right}')
        brief = content(args.brief_file)
        if meta['version'] == 2:
            reserve_handle(db, args.handle, args.name)
            if args.role != 'verifier':
                advance_work(db)
        db.execute('INSERT INTO members(name,handle,role,owns,state,evidence,updated_at) '
                   'VALUES(?,?,?,?,?,?,?)',
                   (args.name, args.handle, args.role, json.dumps(owns),
                    'registered', '', now()))
        return {'seq': append(db, 'coordinator', args.name, brief), 'name': args.name}
    if command == 'state':
        if args.state == 'complete' and not args.evidence_file:
            raise ValueError('completion requires --evidence-file')
        evidence = content(args.evidence_file) if args.evidence_file else ''
        member = get_member(db, args.name)
        if args.reviewed_revision is not None and (
                member['role'] != 'verifier' or args.state != 'complete'):
            raise ValueError('--reviewed-revision is only for verifier completion')
        if meta['version'] == 2:
            if member['role'] == 'verifier' and args.state == 'complete':
                if args.reviewed_revision is None:
                    raise ValueError('verifier completion requires --reviewed-revision from before review')
                if args.reviewed_revision != meta['work_revision']:
                    raise ValueError('stale reviewed revision; inspect the current work again')
            if member['role'] != 'verifier' and (
                    member['state'] != args.state or member['evidence'] != evidence):
                advance_work(db)
            reviewed = args.reviewed_revision if (
                member['role'] == 'verifier' and args.state == 'complete') else None
            db.execute('UPDATE members SET reviewed_revision=? WHERE name=?',
                       (reviewed, args.name))
            if args.state not in ('complete', 'interrupted'):
                clear_inactive_observation(db, args.name)
        elif args.reviewed_revision is not None:
            raise ValueError('--reviewed-revision requires explicit migrate first')
        db.execute('UPDATE members SET state=?,evidence=?,updated_at=? WHERE name=?',
                   (args.state, evidence, now(), args.name))
        return {'seq': append(db, 'coordinator', args.name,
                              f'[state] {args.state}' + (f'\n{evidence}' if evidence else ''))}
    if command in ('post', 'result'):
        known = {row['name'] for row in members(db)} | {'coordinator'}
        if args.author not in known or args.to not in known | {'all'}:
            raise ValueError('unknown sender or recipient; register the member first')
        text = content(args.text_file)
        channel = name(args.channel)
        if meta['version'] == 2 and args.author != 'coordinator':
            clear_inactive_observation(db, args.author)
        if command == 'result':
            if args.author == 'coordinator' or get_member(db, args.author)['role'] != 'verifier':
                advance_work(db)
            text = '[result] ' + text
        return {'seq': append(db, args.author, args.to, text, channel),
                'delivered': False, 'notice': 'Notify the recipient with native agent messaging.'}
    if command == 'observe':
        member = get_member(db, args.name)
        if member['handle'] != args.handle:
            raise ValueError('native observation handle is stale; inspect the current binding')
        evidence = content(args.evidence_file)
        observed_at = now()
        db.execute('UPDATE members SET native_state=?,native_evidence=?,native_observed_at=? '
                   'WHERE name=?', (args.native_state, evidence, observed_at, args.name))
        return {'seq': append(db, 'coordinator', args.name,
                    f'[observe] {args.handle}: {args.native_state}\n{evidence}'),
                'native_observed_at': observed_at, 'live': False}
    if command == 'rebind':
        member = get_member(db, args.name)
        if member['handle'] != args.expected_handle:
            raise ValueError('expected handle is stale; inspect the current binding')
        if (member['native_state'] not in INACTIVE_STATES or
                not member['native_evidence'].strip() or not member['native_observed_at']):
            raise ValueError('rebind requires an explicit inactive native observation with evidence')
        nonblank(args.handle, 'native handle', 300)
        evidence = content(args.evidence_file)
        reserve_handle(db, args.handle, args.name)
        db.execute("UPDATE members SET handle=?,state='registered',evidence='',updated_at=?,"
                   "reviewed_revision=NULL,native_state='unknown',native_evidence='',"
                   "native_observed_at='' WHERE name=?", (args.handle, now(), args.name))
        if member['role'] != 'verifier':
            advance_work(db)
        return {'seq': append(db, 'coordinator', args.name,
                    f'[rebind] {args.expected_handle} -> {args.handle}; '
                    f'observed {member["native_state"]} at {member["native_observed_at"]}\n{evidence}'),
                'name': args.name, 'handle': args.handle, 'spawned': False}
    if command == 'finish':
        summary = content(args.summary_file)
        if args.outcome == 'completed':
            registered = members(db)
            if not registered or any(m['state'] != 'complete' for m in registered):
                raise ValueError('every member must be complete with evidence')
            if not any(m['role'] == 'verifier' for m in registered):
                raise ValueError('a separate verifier is required for completion')
            if not any(m['role'] in ('author', 'reader') for m in registered):
                raise ValueError('a separate author or reader is required for completion')
            if any(m['role'] == 'verifier' and m['reviewed_revision'] != meta['work_revision']
                   for m in registered):
                raise ValueError('stale verifier evidence; review the current work revision again')
        db.execute('UPDATE meta SET outcome=? WHERE id=1', (args.outcome,))
        marker = 'done' if args.outcome == 'completed' else 'cancelled'
        return {'seq': append(db, 'coordinator', 'all', f'[{marker}] {summary}'),
                'outcome': args.outcome,
                'notice': 'This does not stop agents; use native controls separately.'}
    raise ValueError('unsupported command')


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument('--db', required=True, type=Path, help='Exact per-run SQLite board path')
    sub = root.add_subparsers(dest='command', required=True)
    sub.add_parser('init').add_argument('--title', required=True)
    sub.add_parser('status')
    sub.add_parser('migrate', help='Explicit atomic upgrade from schema 1; no automatic migration')
    read = sub.add_parser('read')
    read.add_argument('--since', type=int, default=0)
    read.add_argument('--limit', type=int, default=100)
    read.add_argument('--channel')
    member = sub.add_parser('member', help='Record an existing native agent; does not spawn')
    member.add_argument('--name', required=True)
    member.add_argument('--handle', required=True)
    member.add_argument('--role', required=True, choices=('author', 'reader', 'verifier'))
    member.add_argument('--owns', action='append', default=[])
    member.add_argument('--brief-file', required=True)
    state = sub.add_parser('state', help='Coordinator records observed state')
    state.add_argument('--name', required=True)
    state.add_argument('--state', required=True, choices=STATES)
    state.add_argument('--evidence-file')
    state.add_argument('--reviewed-revision', type=int,
                       help='Verifier completion: revision captured before inspecting work')
    for command in ('post', 'result'):
        post = sub.add_parser(command, help='Record chatter' if command == 'post' else
                              'Record material output; invalidates prior verification')
        post.add_argument('--author', required=True)
        post.add_argument('--to', required=True)
        post.add_argument('--text-file', required=True, help='UTF-8 path or - for stdin')
        post.add_argument('--channel', default='main', help='Label only; no subscriptions or wakeups')
    observe = sub.add_parser('observe', help='Record native observation; never queries live state')
    observe.add_argument('--name', required=True)
    observe.add_argument('--handle', required=True, help='Must match the current binding')
    observe.add_argument('--native-state', required=True, choices=NATIVE_STATES)
    observe.add_argument('--evidence-file', required=True)
    rebind = sub.add_parser('rebind', help='Replace a confirmed inactive binding; does not spawn')
    rebind.add_argument('--name', required=True)
    rebind.add_argument('--expected-handle', required=True)
    rebind.add_argument('--handle', required=True)
    rebind.add_argument('--evidence-file', required=True)
    finish = sub.add_parser('finish')
    finish.add_argument('--outcome', choices=('completed', 'cancelled'), default='completed')
    finish.add_argument('--summary-file', required=True)
    return root


def main():
    args = parser().parse_args()
    path = args.db.absolute()
    try:
        if path.is_symlink():
            raise ValueError('board must not be a symbolic link')
        if args.command == 'init':
            result = initialize(path, args.title)
        else:
            readonly = args.command in ('status', 'read')
            mode = 'ro' if readonly else 'rw'
            with closing(sqlite3.connect(path.as_uri() + '?mode=' + mode,
                                         uri=True, timeout=10)) as db:
                db.row_factory = sqlite3.Row
                # One transaction covers ownership checks and insertion, including concurrent callers.
                db.execute('BEGIN' if readonly else 'BEGIN IMMEDIATE')
                with db:
                    result = run(db, args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'board: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
