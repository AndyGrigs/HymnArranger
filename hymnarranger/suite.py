"""Сценарій: тема + варіації. Порядок і набір розділів залежать від розміру."""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Optional, List

from music21 import stream

from .parsing import parse_input
from .assembly import arrange, arrange_multi
from . import meters


# Режими, де мелодію веде ліва рука: там свій супровід, патерн не чіпаємо
_MELODY_IN_BASS = ('bass_melody_single', 'bass_melody_chords',
                   'bass_melody_dyad', 'bass_melody_thirds')


def resolve_suite(ts, plan=None, seed: Optional[int] = None) -> List[str]:
    """Розгортає план у конкретний список пресетів.
    seed фіксує випадковий вибір — потрібно для відтворюваності."""
    rng = random.Random(seed)
    out = []
    for step in (plan or meters.suite_plan(ts)):
        out.append(rng.choice(step) if isinstance(step, (list, tuple)) else step)
    return out


def arrange_suite(source, plan=None, seed: Optional[int] = None,
                  vary_bass: bool = True) -> stream.Score:
    """
    Повна п'єса: тема + варіації, склеєні в одну партитуру.

    Набір розділів обирається за розміром: у 6/8, 9/8 і 12/8 працює
    тридольний план з арпеджіо, у 2/4, 3/4 і 4/4 — звичайний.
    """
    ctx = parse_input(source)
    for w in ctx.warnings:
        print('  [!] ' + w)

    ts = ctx.ts
    kind = 'тридольний' if meters.is_compound(ts) else 'дводольний'
    print(f'  Розмір {ts.ratioString} -> {kind} план')

    presets = meters.presets(ts)
    pool = meters.lh_pool(ts)
    names = resolve_suite(ts, plan, seed)
    rng = random.Random(None if seed is None else seed + 1000)

    # Тасована колода замість незалежних кидків: інакше один патерн
    # випадає тричі поспіль, а інший жодного разу.
    deck, prev = [], None

    def next_pattern():
        nonlocal deck, prev
        if not deck:
            deck = list(pool)
            rng.shuffle(deck)
            if prev is not None and deck[0] == prev and len(deck) > 1:
                deck[0], deck[1] = deck[1], deck[0]
        prev = deck.pop(0)
        return prev

    cfgs, log = [], []
    for n in names:
        cfg = presets[n]
        if vary_bass and cfg.mode not in _MELODY_IN_BASS:
            pat = next_pattern()
            cfg = replace(cfg, lh_pattern=pat)
            log.append(f'{cfg.name} [бас: {pat}]')
        else:
            log.append(cfg.name)
        cfgs.append(cfg)

    print('  Сюїта:')
    for i, item in enumerate(log, 1):
        print(f'    {i}. {item}')
    return arrange_multi(source, cfgs=cfgs)
