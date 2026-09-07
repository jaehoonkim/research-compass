"""Helper tests; these do not test agent behavior."""
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

    def add(self, text='Requirement: optimize inference.', into='signals', *extra):
        path = self.base / 'input.txt'
        path.write_text(text, encoding='utf-8')
        return self.call('ingest', '--file', str(path), '--into', into, '--title', 'Doc',
                         '--collected-date', '2026-09-07', *extra)

    # init
    def test_init_creates_git_repo_and_layout(self):
        self.assertTrue((self.root / '.git').is_dir())
        for name in ['CLAUDE.md', 'compass.json', 'profile.md', 'roadmap.md', 'journal', 'signals', 'library', 'projects']:
            self.assertTrue((self.root / name).exists(), name)
        log = subprocess.run(['git', '-C', str(self.root), 'log', '--oneline'], capture_output=True, text=True)
        self.assertEqual(len(log.stdout.strip().splitlines()), 1)
        self.assertEqual(self.call('check')['status'], 'ok')

    def test_init_is_idempotent_and_preserves_edits(self):
        p = self.root / 'profile.md'
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

    # ingest
    def test_ingest_preserves_bytes_and_unknowns(self):
        item = self.add()
        folder = self.root / 'signals' / item['id']
        self.assertTrue(item['id'].startswith('SIG-20260907-'))
        self.assertEqual((folder / 'original.txt').read_bytes(), (self.base / 'input.txt').read_bytes())
        meta = json.loads((folder / 'meta.json').read_text())
        self.assertIsNone(meta['organization'])
        self.assertIsNone(meta['published_date'])
        self.assertTrue((folder / 'analysis.md').exists())
        result = self.call('check')
        self.assertEqual(result['counts']['signals'], 1)
        self.assertTrue(result['warnings'])

    def test_library_ingest_uses_lib_prefix_and_notes(self):
        item = self.add('A paper', 'library')
        folder = self.root / 'library' / item['id']
        self.assertTrue(item['id'].startswith('LIB-20260907-'))
        self.assertTrue((folder / 'notes.md').exists())
        meta = json.loads((folder / 'meta.json').read_text())
        self.assertNotIn('demand_group', meta)
        self.assertEqual(self.call('check')['counts']['library'], 1)

    def test_exact_duplicate_returns_same_id(self):
        a, b = self.add(), self.add()
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(b['status'], 'duplicate')
        self.assertEqual(self.call('check')['counts']['signals'], 1)

    def test_same_text_different_known_organizations(self):
        self.add('same', 'signals', '--organization', 'Org A')
        self.add('same', 'signals', '--organization', 'Org B')
        self.assertEqual(self.call('check')['counts']['signals'], 2)

    def test_revision_does_not_increment_demand_groups(self):
        first = self.add('Version one')
        self.add('Version two', 'signals', '--related-to', first['id'], '--relation', 'revision')
        result = self.call('check')
        self.assertEqual(result['counts']['signals'], 2)
        self.assertEqual(result['counts']['demand_groups'], 1)

    def test_missing_related_source_is_rejected(self):
        p = self.base / 'rfp.txt'
        p.write_text('Revised RFP')
        self.call('ingest', '--file', str(p), '--into', 'signals', '--title', 'Revised',
                  '--related-to', 'SIG-20200101-999', '--relation', 'revision', expected=2)
        self.assertEqual(self.call('check')['counts']['signals'], 0)

    def test_invalid_date_is_rejected(self):
        p = self.base / 'date.txt'
        p.write_text('Document')
        self.call('ingest', '--file', str(p), '--into', 'signals', '--title', 'Date',
                  '--published-date', '2026-02-30', expected=2)

    def test_tampered_original_fails(self):
        item = self.add()
        (self.root / 'signals' / item['id'] / 'original.txt').write_text('changed')
        self.assertTrue(any('hash mismatch' in e for e in self.call('check', expected=1)['errors']))

    def test_escaping_original_path_is_rejected(self):
        item = self.add()
        meta = self.root / 'signals' / item['id'] / 'meta.json'
        record = json.loads(meta.read_text())
        record['original_file'] = '../../outside.txt'
        meta.write_text(json.dumps(record))
        self.assertTrue(any('plain filename' in e for e in self.call('check', expected=1)['errors']))


if __name__ == '__main__':
    unittest.main()
