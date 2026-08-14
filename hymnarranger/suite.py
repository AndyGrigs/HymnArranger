"""Сценарій: тема + варіації. Порядок і набір розділів залежать від розміру."""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Optional, List, Tuple

from music21 import stream

from .model import ArrangeConfig
from .parsing import parse_input
from .assembly import arrange_multi
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


def plan_suite(ts, plan=None, seed: Optional[int] = None,
               vary_bass: bool = True) -> List[Tuple[str, ArrangeConfig]]:
    """
    Повертає список (ім'я пресету, готовий cfg) — рівно те, що піде в партитуру.

    Винесено окремо, щоб API міг показати склад сюїти й згенерувати ноти
    з ОДНОГО розрахунку. Інакше при seed=None це були б два незалежні
    випадкові кидки, і підписи розділів не збігалися б із музикою.
    """
    presets = meters.presets(ts)
    pool = meters.lh_pool(ts)
    names = resolve_suite(ts, plan, seed)
    rng = random.Random(None if seed is None else seed + 1000)

    # Тасована колода замість незалежних кидків: інакше один патерн
    # випадає тричі поспіль, а інший жодного разу.
    deck: List[str] = []
    prev: Optional[str] = None

    def next_pattern() -> str:
        nonlocal deck, prev
        if not deck:
            deck = list(pool)
            rng.shuffle(deck)
            if prev is not None and deck[0] == prev and len(deck) > 1:
                deck[0], deck[1] = deck[1], deck[0]
        prev = deck.pop(0)
        return prev

    out: List[Tuple[str, ArrangeConfig]] = []
    for n in names:
        cfg = presets[n]
        if vary_bass and cfg.mode not in _MELODY_IN_BASS:
            cfg = replace(cfg, lh_pattern=next_pattern())
        out.append((n, cfg))
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

    steps = plan_suite(ts, plan, seed, vary_bass)

    print('  Сюїта:')
    for i, (_, cfg) in enumerate(steps, 1):
        print(f'    {i}. {cfg.name} [бас: {cfg.lh_pattern}]')

    return arrange_multi(source, cfgs=[cfg for _, cfg in steps])