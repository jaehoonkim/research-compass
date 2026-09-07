"""Filesystem helper tests; these do not test the behavior of either AI host."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().with_name('compass.py')


class CompassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / 'workspace'
        self.call('init')

    def tearDown(self):
        self.temp.cleanup()

    def call(self, command, *args, expected=0):
        out = subprocess.run([sys.executable, str(SCRIPT), command, '--root', str(self.root), *args],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, expected, out.stdout + out.stderr)
        return json.loads(out.stdout if out.stdout.strip() else out.stderr)

    def add(self, text='Requirement: optimize inference.', kind='job', *extra):
        path = self.base / 'input.txt'
        path.write_text(text, encoding='utf-8')
        return self.call('ingest', '--file', str(path), '--kind', kind, '--title', 'Test document',
                         '--collected-date', '2026-09-07', *extra)

    def test_initialization_and_health(self):
        self.assertEqual(self.call('check')['status'], 'ok')
        self.assertTrue((self.root / 'skills/research-compass/SKILL.md').exists())

    def test_init_is_idempotent_and_preserves_edits(self):
        p = self.root / 'profile/researcher.md'
        p.write_text('User-owned content', encoding='utf-8')
        self.assertEqual(self.call('init')['status'], 'already_initialized')
        self.assertEqual(p.read_text(), 'User-owned content')

    def test_init_refuses_nonempty_unrelated_folder(self):
        root = self.base / 'unrelated'
        root.mkdir()
        (root / 'valuable.txt').write_text('keep')
        result = subprocess.run([sys.executable, str(SCRIPT), 'init', '--root', str(root)], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((root / 'valuable.txt').read_text(), 'keep')

    def test_install_shared_links_idempotently(self):
        self.assertEqual(len(self.call('install')['links_created']), 2)
        self.assertEqual(self.call('install')['links_created'], [])
        for host in ['.claude', '.agents']:
            link = self.root / host / 'skills/research-compass'
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (self.root / "skills/research-compass").resolve())

    def test_install_refuses_conflicts(self):
        p = self.root / '.claude/skills/research-compass'
        p.mkdir(parents=True)
        self.assertEqual(self.call('install', expected=2)['status'], 'error')
        self.assertFalse((self.root / '.agents/skills/research-compass').exists())

    def test_ingest_preserves_bytes_and_unknowns(self):
        item = self.add()
        folder = self.root / 'sources' / item['id']
        self.assertEqual((folder / 'original.txt').read_bytes(), (self.base / 'input.txt').read_bytes())
        meta = json.loads((folder / 'source.json').read_text())
        self.assertIsNone(meta['organization'])
        self.assertIsNone(meta['published_date'])
        result = self.call('check')
        self.assertEqual(result['counts']['job'], 1)
        self.assertTrue(result['warnings'])

    def test_exact_duplicate_does_not_increment_counts(self):
        a, b = self.add(), self.add()
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(b['status'], 'duplicate')
        self.assertEqual(self.call('check')['counts']['total'], 1)

    def test_same_text_different_known_organizations(self):
        self.add('same', 'job', '--organization', 'Org A')
        self.add('same', 'job', '--organization', 'Org B')
        self.assertEqual(self.call('check')['counts']['job'], 2)

    def test_revision_does_not_increment_demand_groups(self):
        first = self.add('Version one', 'rfp')
        self.add('Version two', 'rfp', '--related-to', first['id'], '--relation', 'revision')
        result = self.call('check')
        self.assertEqual(result['counts']['total'], 2)
        self.assertEqual(result['counts']['observed_demand_groups'], 1)

    def test_experiment_is_not_demand(self):
        self.add('Observed test result', 'experiment')
        self.assertEqual(self.call('check')['counts']['observed_demand_groups'], 0)

    def test_lock_protects_helper_writes(self):
        lock = self.call('lock-acquire', '--owner', 'test-session')
        self.call('reindex', expected=2)
        self.call('reindex', '--lock-token', lock['token'])
        self.call('lock-release', '--lock-token', 'wrong-token', expected=2)
        self.call('lock-release', '--lock-token', lock['token'])
        self.assertEqual(self.call('lock-status')['status'], 'unlocked')

    def test_snapshot_excludes_originals(self):
        self.add()
        snap = self.call('snapshot')
        dest = self.root / snap['path']
        self.assertTrue((dest / 'profile/researcher.md').exists())
        self.assertFalse(list(dest.rglob('original.*')))
        self.assertTrue(list(dest.rglob('source.json')))

    def test_tampered_original_fails(self):
        source = self.add()
        (self.root / 'sources' / source['id'] / 'original.txt').write_text('changed')
        self.assertTrue(any('hash mismatch' in e for e in self.call('check', expected=1)['errors']))

    def test_stale_index_is_detected_and_rebuilt(self):
        source = self.add()
        meta = self.root / 'sources' / source['id'] / 'source.json'
        record = json.loads(meta.read_text())
        record['analysis_status'] = 'analyzed'
        meta.write_text(json.dumps(record))
        self.assertTrue(any('stale' in e for e in self.call('check', expected=1)['errors']))
        self.call('reindex')
        self.assertEqual(self.call('check')['status'], 'ok')

    def test_unknown_evidence_reference_fails(self):
        (self.root / 'research/RES-001.md').write_text('Evidence: SRC-20200101-999', encoding='utf-8')
        self.assertTrue(any('unresolved ID' in e for e in self.call('check', expected=1)['errors']))

    def test_missing_related_source_is_rejected(self):
        p = self.base / 'rfp.txt'
        p.write_text('Revised RFP')
        self.call('ingest', '--file', str(p), '--kind', 'rfp', '--title', 'Revised',
                  '--related-to', 'SRC-20200101-999', '--relation', 'revision', expected=2)
        self.assertEqual(self.call('check')['counts']['total'], 0)

    def test_invalid_date_is_rejected(self):
        p = self.base / 'date.txt'
        p.write_text('Document')
        self.call('ingest', '--file', str(p), '--kind', 'job', '--title', 'Date',
                  '--published-date', '2026-02-30', expected=2)
        self.assertEqual(self.call('check')['counts']['total'], 0)

    def test_escaping_original_path_is_rejected(self):
        source = self.add()
        meta = self.root / 'sources' / source['id'] / 'source.json'
        record = json.loads(meta.read_text())
        record['original_file'] = '../../outside.txt'
        meta.write_text(json.dumps(record))
        result = self.call('check', expected=1)
        self.assertTrue(any('plain filename' in e for e in result['errors']))


if __name__ == '__main__':
    unittest.main()
