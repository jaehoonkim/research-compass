#!/usr/bin/env python3
"""Research workspace helper. Python 3.9+, standard library, no network calls."""
from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

SKILL = Path(__file__).resolve().parents[1]
STAGES = ['direction', 'reading', 'reproduction', 'question', 'pilot', 'plan', 'active', 'writeup', 'release']
PROJECT_STATUS = ('active', 'paused', 'completed', 'dropped')
EXP_KINDS = ('reproduction', 'pilot', 'main')
EXP_STATUS = ('planned', 'running', 'completed', 'blocked', 'inconclusive')
GATE = {'reproduction': 'reading', 'pilot': 'question', 'main': 'plan'}
# store -> (id prefix, analysis filename, template filename)
STORES = {'signals': ('SIG', 'analysis.md', 'signal-analysis.md'),
          'library': ('LIB', 'notes.md', 'library-notes.md')}
META_KEYS = {'id', 'title', 'organization', 'source_url', 'published_date', 'collected_date',
             'capture_scope', 'visibility', 'original_file', 'original_name', 'sha256',
             'related_to', 'relation', 'analysis_status'}
ID_RE = re.compile(r'\b(?:SIG-\d{8}-\d{3,}|LIB-\d{8}-\d{3,}|P-\d{3,}|EXP-\d{3,})\b')
HEADER_RE = re.compile(r'^([a-z_]+):[ \t]*(.*)$')
SKIP_RE = re.compile(r'^([a-z]+)->([a-z]+) (\d{4}-\d{2}-\d{2}) (.+)$')
PROJECT_DIR_RE = re.compile(r'^(P-\d{3,})-([a-z0-9-]+)$')


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


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            sha.update(block)
    return sha.hexdigest()


def config(root: Path) -> dict:
    c = read_json(safe(root, 'compass.json'))
    if c.get('schema_version') != 2:
        raise ValueError('Unsupported workspace schema version')
    return c


def now(root: Path) -> datetime:
    return datetime.now(ZoneInfo(config(root).get('timezone', 'Asia/Seoul')))


def checked_date(value: str | None) -> str | None:
    if value is not None and date.fromisoformat(value).isoformat() != value:
        raise ValueError('Use dates in YYYY-MM-DD format')
    return value


def render(template: str, **fields: str) -> str:
    text = (SKILL / 'assets/templates' / template).read_text(encoding='utf-8')
    for key, value in fields.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def header(path: Path) -> dict:
    """`key: value` lines from the top of a Markdown file until the first blank line."""
    found: dict = {'skip': []}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            break
        m = HEADER_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key == 'skip':
            found['skip'].append(value)
        else:
            found[key] = value
    return found


def store_records(root: Path, store: str) -> list[dict]:
    prefix = STORES[store][0]
    result = []
    for folder in sorted(safe(root, store).glob(prefix + '-*')):
        if not folder.is_dir():
            continue
        meta = read_json(folder / 'meta.json')
        missing = META_KEYS - set(meta)
        if missing:
            raise ValueError(folder.name + ' missing fields: ' + ', '.join(sorted(missing)))
        if meta['id'] != folder.name or not re.fullmatch(prefix + r'-\d{8}-\d{3,}', meta['id']):
            raise ValueError('ID / directory mismatch: ' + folder.name)
        result.append(meta)
    return result


def initialize(root: Path) -> dict:
    if (root / 'compass.json').exists():
        config(root)
        return {'status': 'already_initialized', 'root': str(root)}
    if root.exists() and any(root.iterdir()):
        raise ValueError('Refusing to initialize a nonempty directory without compass.json')
    if root.resolve().is_relative_to(SKILL):
        raise ValueError('Workspace must be outside the skill directory')
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL / 'assets/workspace', root, dirs_exist_ok=True)
    git = ['git', '-C', str(root), '-c', 'user.name=research-compass', '-c', 'user.email=compass@localhost']
    result = {'status': 'initialized', 'root': str(root), 'git': 'initialized'}
    try:
        subprocess.run(git[:3] + ['init', '-q'], check=True, capture_output=True)
        subprocess.run(git + ['add', '-A'], check=True, capture_output=True)
        subprocess.run(git + ['commit', '-q', '-m', 'init research workspace'], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        result['git'] = 'failed: ' + str(exc)
    return result


def ingest(root: Path, a: argparse.Namespace) -> dict:
    origin = Path(a.file).expanduser().resolve()
    if not origin.is_file():
        raise ValueError('Input is not a readable local file: ' + str(origin))
    if not a.title.strip():
        raise ValueError('Title must not be empty')
    store = a.into
    prefix, analysis_name, template = STORES[store]
    collected = checked_date(a.collected_date) or now(root).date().isoformat()
    published = checked_date(a.published_date)
    if bool(a.related_to) != bool(a.relation):
        raise ValueError('--related-to and --relation must be supplied together')
    rows = store_records(root, store)
    by_id = {r['id']: r for r in rows}
    if a.related_to and a.related_to not in by_id:
        raise ValueError('Related record does not exist in ' + store + ': ' + a.related_to)
    original_hash = digest(origin)
    for item in rows:
        same_org = (item['organization'] or '').strip().casefold() == (a.organization or '').strip().casefold()
        if item['sha256'] == original_hash and same_org:
            return {'status': 'duplicate', 'id': item['id'],
                    'note': 'Original retained; nothing changed. Record any new provenance separately.'}
    id_prefix = prefix + '-' + collected.replace('-', '') + '-'
    numbers = [int(r['id'].rsplit('-', 1)[1]) for r in rows if r['id'].startswith(id_prefix)]
    sid = id_prefix + str(max(numbers, default=0) + 1).zfill(3)
    suffix = origin.suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,12}', suffix):
        suffix = '.bin'
    raw_name = 'original' + suffix
    meta = {'id': sid, 'title': a.title, 'organization': a.organization, 'source_url': a.source_url,
            'published_date': published, 'collected_date': collected, 'capture_scope': a.capture_scope,
            'visibility': a.visibility, 'original_file': raw_name, 'original_name': origin.name,
            'sha256': original_hash, 'related_to': a.related_to, 'relation': a.relation,
            'analysis_status': 'pending'}
    if store == 'signals':
        meta['demand_group'] = by_id[a.related_to]['demand_group'] if a.relation in ('revision', 'repost') else sid
    store_dir = safe(root, store)
    store_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=str(store_dir)))
    try:
        shutil.copyfile(origin, staging / raw_name)
        if digest(staging / raw_name) != original_hash:
            raise ValueError('Input changed while being copied; retry with a stable file')
        write_json(staging / 'meta.json', meta)
        (staging / analysis_name).write_text(render(template, ID=sid, TITLE=a.title), encoding='utf-8')
        staging.rename(safe(root, store + '/' + sid))
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {'status': 'ingested', 'id': sid, 'path': store + '/' + sid,
            'note': 'Preserved only; the agent must still read and analyze it.'}


def check_store(root: Path, store: str, errors: list, warnings: list) -> list[dict]:
    prefix, analysis_name, _ = STORES[store]
    rows = store_records(root, store)
    by_id = {r['id']: r for r in rows}
    for item in rows:
        sid = item['id']
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
        if Path(item['original_file']).name != item['original_file']:
            errors.append(sid + ': original_file must be a plain filename')
            continue
        original = safe(root, store + '/' + sid + '/' + item['original_file'])
        if not original.is_file():
            errors.append(sid + ': original is missing')
        elif digest(original) != item['sha256']:
            errors.append(sid + ': original hash mismatch')
        if not safe(root, store + '/' + sid + '/' + analysis_name).is_file():
            errors.append(sid + ': ' + analysis_name + ' missing')
        related, relation = item['related_to'], item['relation']
        if bool(related) != bool(relation) or relation not in (None, 'revision', 'repost', 'related'):
            errors.append(sid + ': invalid relation fields')
        if related and (related not in by_id or related == sid):
            errors.append(sid + ': invalid related record')
        if store == 'signals':
            expected = sid
            if relation in ('revision', 'repost') and related in by_id:
                expected = by_id[related].get('demand_group')
            if item.get('demand_group') != expected:
                errors.append(sid + ': wrong demand group')
        seen, current = set(), sid
        while current in by_id:
            if current in seen:
                errors.append(sid + ': cyclic relation')
                break
            seen.add(current)
            current = by_id[current]['related_to']
        if item['analysis_status'] != 'analyzed':
            warnings.append(sid + ': analysis ' + item['analysis_status'])
    if list(safe(root, store).glob('.pending-*')):
        warnings.append(store + ': interrupted intake staging directories found')
    return rows


def check(root: Path) -> dict:
    errors, warnings = [], []
    config(root)
    for name in ['CLAUDE.md', 'profile.md', 'roadmap.md']:
        if not safe(root, name).is_file():
            errors.append('Missing required file: ' + name)
    signals = check_store(root, 'signals', errors, warnings)
    library = check_store(root, 'library', errors, warnings)
    groups = {r.get('demand_group') for r in signals} - {None}
    available = {r['id'] for r in signals + library}
    for path in root.rglob('*.md'):
        if path.name.startswith('original.') or '.git' in path.parts:
            continue
        for ref in set(ID_RE.findall(path.read_text(encoding='utf-8'))):
            if ref not in available:
                errors.append(str(path.relative_to(root)) + ': unresolved ID ' + ref)
    return {'status': 'ok' if not errors else 'failed', 'errors': errors, 'warnings': warnings,
            'counts': {'signals': len(signals), 'library': len(library), 'demand_groups': len(groups)},
            'limits': 'Structure, hashes, references, and stage gates only; not prose truth, novelty, '
                      'privacy, extraction completeness, or agent behavior.'}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', required=True, help='Workspace directory')
    for name in ['init', 'check']:
        sub.add_parser(name, parents=[common])
    add = sub.add_parser('ingest', parents=[common])
    add.add_argument('--file', required=True)
    add.add_argument('--into', choices=list(STORES), required=True)
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
            result = {'check': check, 'ingest': lambda r: ingest(r, args)}[args.command](root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('status') == 'failed' else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
