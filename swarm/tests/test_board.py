import concurrent.futures
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/swarm/scripts/board.py'


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'board.sqlite'

    def call(self, *args, body=None, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), '--db', str(self.db), *args],
            input=body, text=True, capture_output=True, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        return result.stderr

    def init(self):
        return self.call('init', '--title', 'Parser rewrite')

    def member(self, name='parser', role='author', owns='src/parser.py'):
        args = ['member', '--name', name, '--handle', '/root/' + name,
                '--role', role, '--brief-file', '-']
        if owns:
            args += ['--owns', owns]
        return self.call(*args, body='Bounded task and acceptance evidence.')

    def complete(self, name):
        status = self.call('status')
        args = ['state', '--name', name, '--state', 'complete', '--evidence-file', '-']
        if status['version'] == 2 and any(
                m['name'] == name and m['role'] == 'verifier' for m in status['members']):
            args += ['--reviewed-revision', str(status['work_revision'])]
        return self.call(*args, body='Observed: focused checks passed.')

    def legacy_init(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executescript('''
                CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
                    title TEXT NOT NULL, outcome TEXT NOT NULL);
                CREATE TABLE members (name TEXT PRIMARY KEY, handle TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL, owns TEXT NOT NULL, state TEXT NOT NULL,
                    evidence TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE messages (seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL, author TEXT NOT NULL, recipient TEXT NOT NULL,
                    channel TEXT NOT NULL, text TEXT NOT NULL);
                INSERT INTO meta VALUES(1,1,'Legacy run','active');
                INSERT INTO messages VALUES(1,'old','coordinator','all','main','Original brief');
            ''')

    def team_complete(self):
        self.init()
        self.member()
        self.member('verify', 'verifier', None)
        self.complete('parser')
        self.complete('verify')

    def observe(self, state='completed', handle='/root/parser'):
        return self.call('observe', '--name', 'parser', '--handle', handle,
                         '--native-state', state, '--evidence-file', '-',
                         body='Native tool observation: old binding is inactive.')

    def test_stale_verifier_cannot_approve_reopened_and_recompleted_work(self):
        self.team_complete()
        self.call('state', '--name', 'parser', '--state', 'running')
        self.complete('parser')
        error = self.call('finish', '--summary-file', '-', body='Stale review', ok=False)
        self.assertIn('stale', error)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Current review')

    def test_material_result_invalidates_review_but_chatter_does_not(self):
        self.team_complete()
        revision = self.call('status')['work_revision']
        self.call('post', '--author', 'parser', '--to', 'all', '--text-file', '-',
                  body='Coordination chatter')
        self.assertEqual(self.call('status')['work_revision'], revision)
        self.call('result', '--author', 'parser', '--to', 'verify', '--text-file', '-',
                  body='Material output changed')
        self.assertGreater(self.call('status')['work_revision'], revision)
        self.call('finish', '--summary-file', '-', body='Stale', ok=False)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Fresh review')

    def test_identical_state_observation_does_not_invalidate_review(self):
        self.team_complete()
        self.complete('parser')
        self.call('finish', '--summary-file', '-', body='Same evidence, current review')

    def test_work_changed_during_review_rejects_old_revision_at_completion(self):
        self.team_complete()
        inspected_revision = self.call('status')['work_revision']
        self.call('result', '--author', 'parser', '--to', 'verify', '--text-file', '-',
                  body='Changed during verification')
        history = self.call('read')
        error = self.call('state', '--name', 'verify', '--state', 'complete',
                         '--evidence-file', '-', '--reviewed-revision', str(inspected_revision),
                         body='Review of old revision', ok=False)
        self.assertIn('stale', error)
        self.assertEqual(self.call('read'), history)
        self.call('finish', '--summary-file', '-', body='Stale review', ok=False)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Freshly reviewed')

    def test_v2_verifier_completion_requires_explicit_reviewed_revision(self):
        self.init()
        self.member('verify', 'verifier', None)
        error = self.call('state', '--name', 'verify', '--state', 'complete',
                          '--evidence-file', '-', body='Unbound review', ok=False)
        self.assertIn('--reviewed-revision', error)

    def test_verifier_result_does_not_invalidate_current_review(self):
        self.team_complete()
        self.call('result', '--author', 'verify', '--to', 'coordinator', '--text-file', '-',
                  body='Review report')
        self.call('finish', '--summary-file', '-', body='Current review')

    def test_read_only_commands_preserve_both_schema_versions_byte_for_byte(self):
        self.legacy_init()
        for version in (1, 2):
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in self.db.parent.iterdir() if p.is_file()}
            self.assertEqual(self.call('status')['version'], version)
            self.call('read', '--limit', '1')
            after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                     for p in self.db.parent.iterdir() if p.is_file()}
            self.assertEqual(after, before)
            if version == 1:
                self.call('migrate')

    def test_explicit_migration_preserves_history_and_rejects_legacy_approval(self):
        self.legacy_init()
        self.member()
        self.member('verify', 'verifier', None)
        self.complete('parser')
        self.complete('verify')
        old = self.call('read')['messages']
        error = self.call('finish', '--summary-file', '-', body='Legacy approval', ok=False)
        self.assertIn('migrate', error)
        self.call('migrate')
        self.assertEqual(self.call('read')['messages'][:len(old)], old)
        self.assertEqual(self.call('status')['members'][0]['state'], 'complete')
        self.call('finish', '--summary-file', '-', body='Unreviewed migration', ok=False)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Reviewed migrated work')

    def test_migration_failure_rolls_back_columns_version_and_history(self):
        self.legacy_init()
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('''CREATE TRIGGER reject_migrate BEFORE UPDATE ON meta
                WHEN NEW.version = 2 BEGIN SELECT RAISE(ABORT, 'migration denied'); END''')
        before = self.db.read_bytes()
        error = self.call('migrate', ok=False)
        self.assertIn('migration denied', error)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(self.call('status')['version'], 1)

    def test_corrupt_or_unknown_schema_is_not_migrated(self):
        self.legacy_init()
        for version in (0, 3):
            with closing(sqlite3.connect(self.db)) as db, db:
                db.execute('UPDATE meta SET version=?', (version,))
            before = self.db.read_bytes()
            self.call('migrate', ok=False)
            self.call('status', ok=False)
            self.assertEqual(self.db.read_bytes(), before)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('UPDATE meta SET version=1')
            db.execute('ALTER TABLE members RENAME COLUMN owns TO broken')
        before = self.db.read_bytes()
        self.call('migrate', ok=False)
        self.assertEqual(self.db.read_bytes(), before)

    def test_migration_is_idempotent(self):
        self.legacy_init()
        self.call('migrate')
        before = self.db.read_bytes()
        self.assertFalse(self.call('migrate')['migrated'])
        self.assertEqual(self.db.read_bytes(), before)

    def test_closed_legacy_history_remains_read_only_without_migration(self):
        self.legacy_init()
        self.call('finish', '--outcome', 'cancelled', '--summary-file', '-', body='Cancelled')
        before = self.db.read_bytes()
        self.call('migrate', ok=False)
        self.assertEqual(self.call('status')['outcome'], 'cancelled')
        self.call('read')
        self.assertEqual(self.db.read_bytes(), before)

    def test_missing_metadata_column_is_reported_without_traceback_or_changes(self):
        self.legacy_init()
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute('ALTER TABLE meta RENAME COLUMN version TO broken')
        before = self.db.read_bytes()
        error = self.call('migrate', ok=False)
        self.assertIn('schema', error)
        self.assertNotIn('Traceback', error)
        self.assertEqual(self.db.read_bytes(), before)

    def test_reader_result_and_coordinator_material_changes_require_new_review(self):
        self.init()
        self.member('research', 'reader', None)
        self.member('verify', 'verifier', None)
        self.complete('research')
        self.complete('verify')
        for author in ('research', 'coordinator'):
            self.call('result', '--author', author, '--to', 'verify', '--text-file', '-',
                      body='Material findings changed')
            self.call('finish', '--summary-file', '-', body='Stale evidence', ok=False)
            self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Current evidence')

    def test_racing_material_result_and_finish_cannot_both_succeed(self):
        self.team_complete()
        def invoke(command):
            args = (['result', '--author', 'parser', '--to', 'verify', '--text-file', '-']
                    if command == 'result' else ['finish', '--summary-file', '-'])
            return subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db), *args],
                input='Material event', text=True, capture_output=True, timeout=20).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(invoke, ('result', 'finish')))
        self.assertEqual(codes.count(0), 1)

    def test_failed_rebind_retains_observation_completion_and_history(self):
        self.team_complete()
        self.observe()
        before = self.call('status')
        history = self.call('read')
        self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                  '--handle', '/root/verify', '--evidence-file', '-', body='Duplicate', ok=False)
        self.assertEqual(self.call('status'), before)
        self.assertEqual(self.call('read'), history)

    def test_latest_active_observation_prevents_rebind(self):
        self.init()
        self.member()
        self.observe()
        self.observe('running')
        self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                  '--handle', '/root/replacement', '--evidence-file', '-', body='Old evidence',
                  ok=False)

    def test_reopened_task_clears_old_inactive_snapshot_before_rebind(self):
        self.init()
        self.member()
        self.observe()
        self.call('state', '--name', 'parser', '--state', 'running')
        worker = self.call('status')['members'][0]
        self.assertEqual(worker['native_state'], 'unknown')
        self.assertEqual(worker['native_observed_at'], '')
        self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                  '--handle', '/root/replacement', '--evidence-file', '-', body='Old evidence',
                  ok=False)
        self.observe()
        self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                  '--handle', '/root/replacement', '--evidence-file', '-', body='Fresh observation')

    def test_worker_messages_clear_earlier_inactive_snapshot(self):
        self.init()
        self.member()
        for command in ('post', 'result'):
            self.observe()
            revision = self.call('status')['work_revision']
            self.call(command, '--author', 'parser', '--to', 'coordinator', '--text-file', '-',
                      body='Worker activity since previous native observation')
            status = self.call('status')
            self.assertEqual(status['members'][0]['native_state'], 'unknown')
            if command == 'post':
                self.assertEqual(status['work_revision'], revision)
            self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                      '--handle', '/root/replacement', '--evidence-file', '-', body='Old evidence',
                      ok=False)

    def test_observed_native_state_is_separate_from_recorded_task_state(self):
        self.init()
        self.member()
        self.observe('idle')
        worker = self.call('status')['members'][0]
        self.assertEqual(worker['state'], 'registered')
        self.assertEqual(worker['native_state'], 'idle')
        self.assertTrue(worker['native_observed_at'])
        self.assertIn('Recorded', self.call('status')['notice'])

    def test_rebind_requires_inactive_observation_and_expected_current_handle(self):
        self.init()
        self.member()
        args = ['rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                '--handle', '/root/replacement', '--evidence-file', '-']
        self.call(*args, body='Replace', ok=False)
        self.observe('idle')
        self.call(*args, body='Replace', ok=False)
        self.observe()
        before = self.call('status')['work_revision']
        self.call(*args, body='Confirmed inactive; preserve task and ownership.')
        worker = self.call('status')['members'][0]
        self.assertEqual(worker['handle'], '/root/replacement')
        self.assertEqual(worker['owns'], ['src/parser.py'])
        self.assertEqual(worker['state'], 'registered')
        self.assertEqual(worker['evidence'], '')
        self.assertEqual(worker['native_state'], 'unknown')
        self.assertGreater(self.call('status')['work_revision'], before)
        event = self.call('read')['messages'][-1]['text']
        self.assertIn('/root/parser', event)
        self.assertIn('/root/replacement', event)
        self.call(*args, body='Old expected binding is stale', ok=False)
        self.call('observe', '--name', 'parser', '--handle', '/root/parser',
                  '--native-state', 'completed', '--evidence-file', '-',
                  body='Stale observation', ok=False)

    def test_rebind_preserves_old_handles_and_refuses_handle_reuse(self):
        self.init()
        self.member()
        self.observe()
        self.call('rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                  '--handle', '/root/replacement', '--evidence-file', '-', body='Inactive')
        self.call('member', '--name', 'reader', '--handle', '/root/parser',
                  '--role', 'reader', '--brief-file', '-', body='Reused handle', ok=False)

    def test_racing_rebinds_change_binding_once_without_losing_history(self):
        self.init()
        self.member()
        self.observe()
        def rebind(i):
            return subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db),
                'rebind', '--name', 'parser', '--expected-handle', '/root/parser',
                '--handle', f'/root/replacement-{i}', '--evidence-file', '-'],
                input='Confirmed inactive', text=True, capture_output=True, timeout=20).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(rebind, range(4)))
        self.assertEqual(codes.count(0), 1)
        events = [m for m in self.call('read')['messages'] if m['text'].startswith('[rebind]')]
        self.assertEqual(len(events), 1)
        self.assertEqual(len(self.call('status')['members']), 1)

    def test_missing_board_read_does_not_create_files(self):
        self.call('read', ok=False)
        self.assertFalse(self.db.exists())

    def test_init_preserves_existing_board_and_private_permissions(self):
        self.init()
        self.call('init', '--title', 'Wrong task', ok=False)
        self.assertEqual(self.call('status')['title'], 'Parser rewrite')
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)

    def test_concurrent_process_posts_have_unique_ordered_sequences(self):
        self.init()
        def post(i):
            return self.call('post', '--author', 'coordinator', '--to', 'all',
                             '--text-file', '-', body=f'Result {i}')['seq']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            seqs = list(pool.map(post, range(32)))
        self.assertEqual(len(set(seqs)), 32)
        messages = self.call('read')['messages']
        found = [m for m in messages if m['text'].startswith('Result ')]
        self.assertEqual(len(found), 32)
        self.assertEqual([m['seq'] for m in found], sorted(seqs))

    def test_pagination_cursor_never_skips_unseen_posts(self):
        self.init()
        for i in range(4):
            self.call('post', '--author', 'coordinator', '--to', 'all',
                      '--text-file', '-', body=str(i))
        first = self.call('read', '--limit', '2')
        self.assertTrue(first['has_more'])
        self.assertEqual(first['next_since'], first['messages'][-1]['seq'])
        second = self.call('read', '--since', str(first['next_since']))
        self.assertEqual(len(first['messages']) + len(second['messages']), 5)

    def test_unknown_sender_or_recipient_rejected(self):
        self.init()
        for sender, recipient in [('ghost', 'all'), ('coordinator', 'ghost')]:
            self.call('post', '--author', sender, '--to', recipient,
                      '--text-file', '-', body='Hello', ok=False)

    def test_member_brief_and_native_handle_survive_new_process(self):
        self.init()
        self.member()
        status = self.call('status')
        self.assertEqual(status['members'][0]['handle'], '/root/parser')
        self.assertEqual(status['members'][0]['state'], 'registered')
        self.assertIn('Bounded task', self.call('read')['messages'][-1]['text'])

    def test_overlapping_directory_ownership_and_reused_names_rejected(self):
        self.init()
        self.member(owns='src')
        error = self.call('member', '--name', 'other', '--handle', '/root/other',
                         '--role', 'author', '--owns', 'src/parser.py',
                         '--brief-file', '-', body='Task', ok=False)
        self.assertIn('ownership', error)
        self.call('member', '--name', 'parser', '--handle', '/root/duplicate',
                  '--role', 'reader', '--brief-file', '-', body='Task', ok=False)

    def test_verifier_cannot_claim_files(self):
        self.init()
        self.call('member', '--name', 'verify', '--handle', '/root/verify',
                  '--role', 'verifier', '--owns', 'src', '--brief-file', '-',
                  body='Review', ok=False)

    def test_unsafe_ownership_paths_rejected(self):
        self.init()
        for path in ['../escape', '/absolute', 'src/../other', 'src/*', '.']:
            self.call('member', '--name', 'parser', '--handle', '/root/parser',
                      '--role', 'author', '--owns', path, '--brief-file', '-',
                      body='Task', ok=False)

    def test_completion_requires_verifier_and_evidence(self):
        self.init()
        self.member()
        self.call('state', '--name', 'parser', '--state', 'complete', ok=False)
        self.complete('parser')
        self.call('finish', '--summary-file', '-', body='Done', ok=False)
        self.member('verify', 'verifier', None)
        self.call('finish', '--summary-file', '-', body='Done', ok=False)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='Checks passed')
        self.assertEqual(self.call('status')['outcome'], 'completed')
        self.assertIn('[done]', self.call('read')['messages'][-1]['text'])
        self.call('post', '--author', 'coordinator', '--to', 'all',
                  '--text-file', '-', body='Too late', ok=False)

    def test_cancel_keeps_history_without_claiming_completion(self):
        self.init()
        self.member()
        self.call('finish', '--outcome', 'cancelled', '--summary-file', '-',
                  body='User cancelled; native agent interruption checked separately.')
        self.assertEqual(self.call('status')['outcome'], 'cancelled')
        self.assertEqual(self.call('status')['members'][0]['state'], 'registered')

    def test_failed_mutation_does_not_append_history(self):
        self.init()
        before = self.call('read')
        self.call('state', '--name', 'unknown', '--state', 'running', ok=False)
        self.assertEqual(self.call('read'), before)

    def test_channels_are_filterable_tags_not_delivery(self):
        self.init()
        self.call('post', '--author', 'coordinator', '--to', 'all',
                  '--channel', 'parser', '--text-file', '-', body='Area decision')
        messages = self.call('read', '--channel', 'parser')['messages']
        self.assertEqual([m['text'] for m in messages], ['Area decision'])

    def test_invalid_cursor_or_empty_message_rejected(self):
        self.init()
        self.call('read', '--since', '-1', ok=False)
        self.call('read', '--limit', '0', ok=False)
        self.call('post', '--author', 'coordinator', '--to', 'all',
                  '--text-file', '-', body='  ', ok=False)

    def test_racing_ownership_claims_allow_only_one_author(self):
        self.init()
        def claim(i):
            return subprocess.run(
                [sys.executable, str(SCRIPT), '--db', str(self.db), 'member',
                 '--name', f'worker-{i}', '--handle', f'/root/worker-{i}',
                 '--role', 'author', '--owns', 'src', '--brief-file', '-'],
                input='Task', text=True, capture_output=True, timeout=20).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(claim, range(4)))
        self.assertEqual(codes.count(0), 1)
        self.assertEqual(len(self.call('status')['members']), 1)

    def test_board_text_is_stored_as_data(self):
        self.init()
        message = "'; DROP TABLE members; --\n$(touch unrelated) `whoami`"
        self.call('post', '--author', 'coordinator', '--to', 'all',
                  '--text-file', '-', body=message)
        self.assertEqual(self.call('read')['messages'][-1]['text'], message)
        self.assertEqual(self.call('status')['members'], [])

    def test_symlink_board_is_rejected_without_modifying_target(self):
        self.init()
        target = self.db
        self.db = Path(self.tmp.name) / 'linked.sqlite'
        self.db.symlink_to(target)
        before = target.read_bytes()
        self.call('read', ok=False)
        self.assertEqual(target.read_bytes(), before)

    def test_reopening_work_clears_old_completion_evidence(self):
        self.init()
        self.member()
        self.complete('parser')
        self.call('state', '--name', 'parser', '--state', 'running')
        self.assertEqual(self.call('status')['members'][0]['evidence'], '')

    def test_a_lone_verifier_is_not_an_independent_team(self):
        self.init()
        self.member('verify', 'verifier', None)
        self.complete('verify')
        self.call('finish', '--summary-file', '-', body='No separate worker', ok=False)


if __name__ == '__main__':
    unittest.main()
