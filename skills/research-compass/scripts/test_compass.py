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

    # projects
    def project(self, slug='rvv-quant'):
        return self.call('new-project', '--slug', slug, '--title', 'Test project')

    def set_header(self, path, **fields):
        lines = path.read_text(encoding='utf-8').splitlines()
        end = lines.index('')
        head = [l for l in lines[:end] if l.split(':')[0] not in fields]
        head += [f'{k}: {v}' for k, v in fields.items()]
        path.write_text('\n'.join(head + lines[end:]) + '\n', encoding='utf-8')

    def experiment(self, folder, kind, number=1, **fields):
        p = folder / 'experiments' / f'EXP-{number:03d}.md'
        p.write_text(f'id: EXP-{number:03d}\nkind: {kind}\nstatus: planned\nverdict:\n\n# EXP\n', encoding='utf-8')
        if fields:
            self.set_header(p, **fields)
        return p

    def test_new_project_numbers_and_files(self):
        a = self.project('first')
        b = self.project('second')
        self.assertEqual(a['id'], 'P-001')
        self.assertEqual(b['id'], 'P-002')
        folder = self.root / 'projects/P-002-second'
        self.assertTrue((folder / 'project.md').exists())
        self.assertTrue((folder / 'reading.md').exists())
        self.assertTrue((folder / 'experiments').is_dir())
        self.assertEqual(self.call('check')['projects'][1]['stage'], 'direction')

    def test_new_project_rejects_bad_slug(self):
        self.call('new-project', '--slug', 'Bad Slug', '--title', 'x', expected=2)

    def test_invalid_stage_is_error(self):
        self.project()
        self.set_header(self.root / 'projects/P-001-rvv-quant/project.md', stage='thinking')
        self.assertTrue(any('invalid stage' in e for e in self.call('check', expected=1)['errors']))

    def test_gate_blocks_main_experiment_before_plan(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.set_header(folder / 'project.md', stage='reading')
        self.experiment(folder, 'main')
        errors = self.call('check', expected=1)['errors']
        self.assertTrue(any('gate' in e for e in errors), errors)

    def test_gate_allows_reproduction_at_reading(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.set_header(folder / 'project.md', stage='reading')
        self.experiment(folder, 'reproduction')
        self.assertEqual(self.call('check')['status'], 'ok')

    def test_skip_downgrades_gate_to_warning(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.set_header(folder / 'project.md', stage='reading', skip='reading->plan 2026-09-10 사용자 요청')
        self.experiment(folder, 'main')
        result = self.call('check')
        self.assertEqual(result['status'], 'ok')
        self.assertTrue(any('gate' in w for w in result['warnings']))

    def test_bad_skip_line_is_error(self):
        self.project()
        self.set_header(self.root / 'projects/P-001-rvv-quant/project.md', skip='reading plan whenever')
        self.assertTrue(any('skip' in e for e in self.call('check', expected=1)['errors']))

    def test_invalid_experiment_kind_and_status(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.experiment(folder, 'guess', status='done')
        errors = self.call('check', expected=1)['errors']
        self.assertTrue(any('invalid kind' in e for e in errors))
        self.assertTrue(any('invalid status' in e for e in errors))

    def test_reading_stage_reports_unmet_library_minimum(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.set_header(folder / 'project.md', stage='reading')
        lib = self.add('paper', 'library')['id']
        (folder / 'reading.md').write_text(f'# notes\n{lib}\n', encoding='utf-8')
        unmet = self.call('check')['projects'][0]['unmet']
        self.assertTrue(any('library' in u for u in unmet), unmet)

    def test_pilot_stage_reports_missing_verdict(self):
        self.project()
        folder = self.root / 'projects/P-001-rvv-quant'
        self.set_header(folder / 'project.md', stage='pilot')
        self.experiment(folder, 'pilot', status='completed')
        self.assertTrue(any('verdict' in u for u in self.call('check')['projects'][0]['unmet']))
        self.experiment(folder, 'pilot', status='completed', verdict='alive')
        self.assertEqual(self.call('check')['projects'][0]['unmet'], [])

    def test_unknown_id_reference_in_project_fails(self):
        self.project()
        (self.root / 'projects/P-001-rvv-quant/reading.md').write_text('See LIB-20200101-999', encoding='utf-8')
        self.assertTrue(any('unresolved ID' in e for e in self.call('check', expected=1)['errors']))


if __name__ == '__main__':
    unittest.main()
