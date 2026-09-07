#!/usr/bin/env python3
"""Local research records. Python 3.9+, standard library, no network calls."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo

SKILL = Path(__file__).resolve().parents[1]
LOCK = '.compass-write.lock'
KINDS = ('job', 'rfp', 'reference', 'experiment')
SOURCE_RE = re.compile(r'^SRC-\d{8}-\d{3,}$')
REQUIRED = {'schema_version', 'id', 'kind', 'title', 'organization', 'source_url',
            'published_date', 'collected_date', 'capture_scope', 'visibility',
            'original_file', 'original_name', 'sha256', 'related_to', 'relation',
            'demand_group', 'analysis_status'}


def safe(root: Path, relative: str) -> Path:
    p = root / relative
    if Path(relative).is_absolute() or not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes the workspace: ' + relative)
    return p


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object: ' + str(path))
    return value


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.compass-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def config(root: Path) -> dict:
    c = read_json(safe(root, 'compass.json'))
    if c.get('schema_version') != 1:
        raise ValueError('Unsupported workspace schema version')
    return c


def now(root: Path) -> datetime:
    return datetime.now(ZoneInfo(config(root).get('timezone', 'Asia/Seoul')))


def checked_date(value: str | None) -> str | None:
    if value is not None:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Use dates in YYYY-MM-DD format')
    return value


def acquire(root: Path, owner: str) -> dict:
    path = safe(root, LOCK)
    value = {'token': uuid.uuid4().hex, 'owner': owner,
             'created_at': now(root).isoformat(), 'pid': os.getpid(),
             'note': 'Advisory session lock; PID may end before the session finishes.'}
    try:
        with path.open('x', encoding='utf-8') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
    except FileExistsError:
        raise ValueError('Workspace is locked. Inspect lock status; do not steal it.')
    return value


def release(root: Path, token: str) -> None:
    path = safe(root, LOCK)
    current = read_json(path)
    if not token or current.get('token') != token:
        raise ValueError('Lock token does not match; nothing was removed')
    path.unlink()


@contextmanager
def write_lock(root: Path, token: str | None = None):
    token = token or os.environ.get('COMPASS_LOCK_TOKEN')
    if token:
        current = read_json(safe(root, LOCK))
        if current.get('token') != token:
            raise ValueError('Lock token does not match')
        yield
    else:
        acquired = acquire(root, 'helper-command')
        try:
            yield
        finally:
            release(root, acquired['token'])


def records(root: Path) -> list[dict]:
    result = []
    for folder in sorted(safe(root, 'sources').glob('SRC-*')):
        if not folder.is_dir() or not folder.resolve().is_relative_to(root):
            raise ValueError('Invalid source directory: ' + str(folder))
        meta = read_json(folder / 'source.json')
        missing = REQUIRED - set(meta)
        if missing:
            raise ValueError(folder.name + ' missing fields: ' + ', '.join(sorted(missing)))
        if meta['id'] != folder.name or not SOURCE_RE.fullmatch(meta['id']):
            raise ValueError('Source ID / directory mismatch: ' + folder.name)
        result.append(meta)
    return result


def index_value(root: Path) -> dict:
    rows = records(root)
    groups = {r['demand_group'] for r in rows if r['kind'] in ('job', 'rfp')}
    return {'schema_version': 1,
            'counts': {'total': len(rows),
                       **{kind: sum(r['kind'] == kind for r in rows) for kind in KINDS},
                       'observed_demand_groups': len(groups - {None})},
            'count_note': 'Observed deduplicated records, not verified independent organizations or market demand.',
            'sources': rows}


def reindex(root: Path) -> dict:
    value = index_value(root)
    atomic_json(safe(root, 'index/sources.json'), value)
    return value['counts']


def initialize(root: Path) -> dict:
    if (root / 'compass.json').exists():
        config(root)
        return {'status': 'already_initialized', 'root': str(root)}
    if root.exists() and any(root.iterdir()):
        raise ValueError('Refusing to initialize a nonempty directory without compass.json')
    if root.is_relative_to(SKILL):
        raise ValueError('Workspace must be outside the distributable skill directory')
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL / 'assets/workspace', root, dirs_exist_ok=True)
    reindex(root)
    return {'status': 'initialized', 'root': str(root)}


def ingest(root: Path, a: argparse.Namespace) -> dict:
    origin = Path(a.file).expanduser().resolve()
    if not origin.is_file():
        raise ValueError('Input is not a readable local file: ' + str(origin))
    if not a.title.strip():
        raise ValueError('Title must not be empty')
    collected = checked_date(a.collected_date) or now(root).date().isoformat()
    published = checked_date(a.published_date)
    if bool(a.related_to) != bool(a.relation):
        raise ValueError('--related-to and --relation must be supplied together')
    rows = records(root)
    by_id = {r['id']: r for r in rows}
    if a.related_to and a.related_to not in by_id:
        raise ValueError('Related source does not exist: ' + a.related_to)
    if a.relation in ('revision', 'repost') and by_id[a.related_to]['kind'] != a.kind:
        raise ValueError('Revisions/reposts must keep the same source kind')
    original_hash = digest(origin)
    for item in rows:
        same_org = (item['organization'] or '').strip().casefold() == (a.organization or '').strip().casefold()
        if item['sha256'] == original_hash and item['kind'] == a.kind and same_org:
            return {'status': 'duplicate', 'id': item['id'],
                    'note': 'Original retained; no demand count or file changed. Record any new provenance separately.'}
    prefix = 'SRC-' + collected.replace('-', '') + '-'
    numbers = [int(r['id'].rsplit('-', 1)[1]) for r in rows if r['id'].startswith(prefix)]
    sid = prefix + str(max(numbers, default=0) + 1).zfill(3)
    group = sid if a.kind in ('job', 'rfp') else None
    if a.relation in ('revision', 'repost'):
        group = by_id[a.related_to]['demand_group']
    suffix = origin.suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,12}', suffix):
        suffix = '.bin'
    raw_name = 'original' + suffix
    meta = {'schema_version': 1, 'id': sid, 'kind': a.kind, 'title': a.title,
            'organization': a.organization, 'source_url': a.source_url,
            'published_date': published, 'collected_date': collected,
            'capture_scope': a.capture_scope, 'visibility': a.visibility,
            'original_file': raw_name, 'original_name': origin.name,
            'sha256': original_hash, 'related_to': a.related_to,
            'relation': a.relation, 'demand_group': group, 'analysis_status': 'pending'}
    sources = safe(root, 'sources')
    sources.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.pending-', dir=str(sources)))
    try:
        shutil.copyfile(origin, stage / raw_name)
        if digest(stage / raw_name) != original_hash:
            raise ValueError('Input changed while being copied; retry with a stable file')
        atomic_json(stage / 'source.json', meta)
        template = (SKILL / 'assets/templates/source-analysis.md').read_text(encoding='utf-8')
        (stage / 'analysis.md').write_text(template.replace('{{SOURCE_ID}}', sid).replace('{{TITLE}}', a.title), encoding='utf-8')
        stage.rename(safe(root, 'sources/' + sid))
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    reindex(root)
    return {'status': 'ingested', 'id': sid, 'analysis_status': 'pending',
            'path': 'sources/' + sid, 'note': 'Preserved only; the agent must still inspect and analyze the source.'}


def snapshot(root: Path) -> dict:
    stamp = now(root).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    dest = safe(root, 'snapshots/' + stamp)
    dest.mkdir(parents=True, exist_ok=False)
    copied = []
    roots = ['profile', 'index', 'research', 'experiments', 'roadmap', 'decisions', 'sources']
    paths = [root / 'compass.json']
    for name in roots:
        for path in safe(root, name).rglob('*'):
            if path.suffix in ('.md', '.json') and path.is_file() and not path.name.startswith(('original.', 'extracted.')):
                paths.append(path)
    for path in paths:
        relative = str(path.relative_to(root))
        safe(root, relative)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(relative)
    atomic_json(dest / 'manifest.json', {'created_at': now(root).isoformat(), 'files': copied,
                                       'note': 'Curated state and metadata only; original documents are not duplicated.'})
    return {'status': 'snapshot_created', 'path': str(dest.relative_to(root)), 'files': len(copied)}


def check(root: Path) -> dict:
    errors, warnings = [], []
    config(root)
    for name in ['CLAUDE.md', 'profile/researcher.md', 'index/research-map.md', 'roadmap/current.md']:
        if not safe(root, name).is_file():
            errors.append('Missing required file: ' + name)
    rows = records(root)
    by_id = {r['id']: r for r in rows}
    for item in rows:
        sid = item['id']
        if item['schema_version'] != 1 or item['kind'] not in KINDS:
            errors.append(sid + ': invalid schema/kind')
        if item['analysis_status'] not in ('pending', 'partial', 'analyzed'):
            errors.append(sid + ': invalid analysis status')
        if item['visibility'] not in ('public', 'private', 'unknown'):
            errors.append(sid + ': invalid visibility')
        for field in ('published_date', 'collected_date'):
            try:
                checked_date(item[field])
                if field == 'collected_date' and item[field] is None:
                    raise ValueError('Missing collection date')
            except (ValueError, TypeError):
                errors.append(sid + ': invalid ' + field)
        for field in ('title', 'capture_scope', 'original_name'):
            if not isinstance(item[field], str) or not item[field].strip():
                errors.append(sid + ': missing ' + field)
        if Path(item['original_file']).name != item['original_file']:
            errors.append(sid + ': original_file must be a plain filename')
            continue
        original = safe(root, 'sources/' + sid + '/' + item['original_file'])
        if not original.is_file():
            errors.append(sid + ': original is missing')
        elif digest(original) != item['sha256']:
            errors.append(sid + ': original hash mismatch')
        if not safe(root, 'sources/' + sid + '/analysis.md').is_file():
            errors.append(sid + ': analysis file missing')
        related = item['related_to']
        relation = item['relation']
        if bool(related) != bool(relation) or relation not in (None, 'revision', 'repost', 'related'):
            errors.append(sid + ': invalid relation fields')
        if related and (related not in by_id or related == sid):
            errors.append(sid + ': invalid related source')
        if item['kind'] in ('job', 'rfp'):
            expected = sid
            if relation in ('revision', 'repost') and related in by_id:
                expected = by_id[related]['demand_group']
                if by_id[related]['kind'] != item['kind']:
                    errors.append(sid + ': revision/repost kind mismatch')
            if item['demand_group'] != expected:
                errors.append(sid + ': wrong demand group')
        elif item['demand_group'] is not None:
            errors.append(sid + ': non-demand source has a demand group')
        seen, current = set(), sid
        while current in by_id:
            if current in seen:
                errors.append(sid + ': cyclic source relation')
                break
            seen.add(current)
            current = by_id[current]['related_to']
        if item['analysis_status'] != 'analyzed':
            warnings.append(sid + ': analysis ' + item['analysis_status'])
    try:
        if read_json(safe(root, 'index/sources.json')) != index_value(root):
            errors.append('Source index is stale; run reindex')
    except (OSError, ValueError):
        errors.append('Source index missing or invalid; run reindex')
    available = set(by_id)
    for folder, prefix in [('research', 'RES'), ('experiments', 'EXP')]:
        available.update(p.stem for p in safe(root, folder).glob(prefix + '-[0-9]*.md'))
    ref_pattern = re.compile(r'\b(?:SRC-\d{8}-\d{3,}|RES-\d{3,}|EXP-\d{3,})\b')
    for folder in ['index', 'research', 'experiments', 'roadmap', 'decisions', 'sources']:
        for path in safe(root, folder).rglob('*.md'):
            if path.name.startswith(('original.', 'extracted.')):
                continue
            safe(root, str(path.relative_to(root)))
            for ref in set(ref_pattern.findall(path.read_text(encoding='utf-8'))):
                if ref not in available:
                    errors.append(str(path.relative_to(root)) + ': unresolved ID ' + ref)
    pending = list(safe(root, 'sources').glob('.pending-*'))
    if pending:
        warnings.append('Interrupted intake staging directories found; inspect before cleanup')
    return {'status': 'ok' if not errors else 'failed', 'errors': errors, 'warnings': warnings,
            'counts': index_value(root)['counts'],
            'limits': 'Structure/hashes/references only; not prose truth, novelty, privacy, extraction completeness, or agent behavior.'}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', required=True, help='Explicit workspace directory')
    common.add_argument('--lock-token', help='Token from lock-acquire for multi-file work')
    for name in ['init', 'reindex', 'check', 'snapshot', 'lock-status', 'lock-release']:
        sub.add_parser(name, parents=[common])
    lock = sub.add_parser('lock-acquire', parents=[common])
    lock.add_argument('--owner', required=True, help='Descriptive session name')
    add = sub.add_parser('ingest', parents=[common])
    add.add_argument('--file', required=True)
    add.add_argument('--kind', choices=KINDS, required=True)
    add.add_argument('--title', required=True)
    add.add_argument('--organization')
    add.add_argument('--source-url')
    add.add_argument('--published-date')
    add.add_argument('--collected-date')
    add.add_argument('--capture-scope', default='user-provided file; completeness not yet verified')
    add.add_argument('--visibility', choices=['public', 'private', 'unknown'], default='private')
    add.add_argument('--related-to')
    add.add_argument('--relation', choices=['revision', 'repost', 'related'])
    return p


def main() -> int:
    args = parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    try:
        if args.command == 'init':
            result = initialize(root)
        else:
            config(root)
            if args.command == 'check':
                result = check(root)
            elif args.command == 'lock-acquire':
                result = acquire(root, args.owner)
            elif args.command == 'lock-status':
                path = safe(root, LOCK)
                result = {'status': 'locked', **read_json(path)} if path.exists() else {'status': 'unlocked'}
            elif args.command == 'lock-release':
                release(root, args.lock_token or os.environ.get('COMPASS_LOCK_TOKEN', ''))
                result = {'status': 'unlocked'}
            else:
                with write_lock(root, args.lock_token):
                    if args.command == 'ingest':
                        result = ingest(root, args)
                    elif args.command == 'snapshot':
                        result = snapshot(root)
                    else:
                        result = {'status': 'reindexed', 'counts': reindex(root)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') == 'failed' else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
