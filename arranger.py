#!/usr/bin/env python3
"""Запускач HymnArranger. Уся логіка — у пакеті hymnarranger/."""

import argparse
from pathlib import Path

from hymnarranger import arrange, arrange_suite, arrange_multi, parse_input, save
from hymnarranger import meters

HERE = Path(__file__).resolve().parent
IN_DIR = HERE / 'input'
OUT_DIR = HERE / 'output'


def _pick_input(explicit=None):
    if explicit:
        return Path(explicit)
    IN_DIR.mkdir(exist_ok=True)
    files = sorted([p for p in IN_DIR.iterdir()
                    if p.suffix.lower() in ('.mxl', '.musicxml', '.xml')])
    if not files:
        raise SystemExit(f'У теці {IN_DIR} немає файлів .mxl / .musicxml')
    return files[0]


def main():
    ap = argparse.ArgumentParser(description='Генератор баянного аранжування')
    ap.add_argument('input', nargs='?', help='вхідний MusicXML (типово — перший із input/)')
    ap.add_argument('-o', '--output')
    ap.add_argument('-p', '--preset')
    ap.add_argument('--all', action='store_true', help='усі пресети окремими файлами')
    ap.add_argument('--merge', action='store_true', help='усі пресети в одній партитурі')
    ap.add_argument('--suite', action='store_true', help="готова п'єса: тема + варіації")
    ap.add_argument('--seed', type=int, default=None, help='зерно для --suite')
    ap.add_argument('--list', action='store_true', help='показати пресети для цього файлу')
    a = ap.parse_args()

    in_path = _pick_input(a.input)
    OUT_DIR.mkdir(exist_ok=True)
    out_path = Path(a.output) if a.output else OUT_DIR / (in_path.stem + '.mxl')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f'Вхідний файл: {in_path}')

    ts = parse_input(str(in_path)).ts
    PRESETS = meters.presets(ts)

    if a.list:
        kind = 'тридольний' if meters.is_compound(ts) else 'дводольний'
        print(f'Розмір {ts.ratioString} -> {kind} набір:')
        for k, c in PRESETS.items():
            print(f'  {k:18s} {c.name}')
        return

    if a.suite:
        save(arrange_suite(str(in_path), seed=a.seed), out_path)
        print(f'Сюїта -> {out_path}')
    elif a.merge:
        save(arrange_multi(str(in_path), presets=list(PRESETS),
                           preset_map=PRESETS), out_path)
        print(f'Склеєна партитура ({len(PRESETS)} розділів) -> {out_path}')
    elif a.all:
        for nm, cfg in PRESETS.items():
            fp = out_path.with_name(f'{out_path.stem}__{nm}.mxl')
            save(arrange(str(in_path), cfg), fp)
            print(f'{cfg.name:34s} -> {fp}')
    else:
        name = a.preset or next(iter(PRESETS))
        if name not in PRESETS:
            raise SystemExit(f'Пресет {name!r} недоступний для розміру {ts.ratioString}. '
                             f'Доступні: {", ".join(PRESETS)}')
        save(arrange(str(in_path), PRESETS[name]), out_path)
        print(f'{PRESETS[name].name} -> {out_path}')


if __name__ == '__main__':
    main()