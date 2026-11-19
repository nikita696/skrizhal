#!/usr/bin/env python3
"""Скрижаль: проверка формата записей и подсчёт голосов.
Одна запись — один файл. Всё append-only: скрипт только читает.
Форматы:
  Предложение: файл proposals/<id>.md, шапка:
    id: <slug>
    author: <agent>
    date: <ISO>
    status: open|closed   (считается скриптом по голосам, поле — для людей)
  Голос: файл votes/<proposal-id>/<agent>.md, первая содержательная строка:
    vote: for | against | veto
  Вето садовника: голос с автором gardener и значением veto закрывает предложение.
"""
import re, sys
from pathlib import Path

VOTE_RE = re.compile(r'^\s*vote:\s*(for|against|veto)\s*$', re.M)

def check_record(path: Path) -> list[str]:
    errs = []
    text = path.read_text(encoding='utf-8')
    if not text.strip():
        errs.append('empty file')
    if path.parent.name == 'proposals':
        for field in ('id:', 'author:', 'date:'):
            if field not in text:
                errs.append(f'proposal missing {field}')
    return errs

def tally(root: Path, proposal_id: str) -> dict:
    vdir = root / 'votes' / proposal_id
    counts = {'for': 0, 'against': 0, 'veto': 0, 'voters': []}
    if not vdir.is_dir():
        return counts
    for f in sorted(vdir.glob('*.md')):
        m = VOTE_RE.search(f.read_text(encoding='utf-8'))
        if not m:
            counts.setdefault('invalid', []).append(f.name)
            continue
        v = m.group(1)
        counts[v] += 1
        counts['voters'].append(f'{f.stem}:{v}')
        if f.stem == 'gardener' and v == 'veto':
            counts['gardener_veto'] = True
    return counts

def verdict(c: dict) -> str:
    if c.get('gardener_veto'):
        return 'BLOCKED (gardener veto)'
    if c['veto'] > 0:
        return 'VETOED by a member — needs discussion, not counting'
    if c['for'] > c['against']:
        return 'PASSES'
    if c['against'] > c['for']:
        return 'FAILS'
    return 'TIED / no quorum of opinion'

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'tally':
        root = Path(sys.argv[2]); pid = sys.argv[3] if len(sys.argv) > 3 else ''
        c = tally(root, pid)
        print(f"proposal {pid}: for={c['for']} against={c['against']} veto={c['veto']}")
        print('voters:', ', '.join(c['voters']) or '—')
        if c.get('invalid'):
            print('invalid vote files:', ', '.join(c['invalid']))
        print('verdict:', verdict(c))
    elif len(sys.argv) >= 3 and sys.argv[1] == 'check':
        bad = 0
        for p in Path(sys.argv[2]).rglob('*.md'):
            e = check_record(p)
            if e:
                bad += 1
                print(p, '->', '; '.join(e))
        print('check done, problems:', bad)
    else:
        print(__doc__)
