"""Змішування фактур усередині однієї варіації: кожна фраза — своя фактура.

Ідея: кожен пресет будується на ВЕСЬ гімн, а потім з кожного вирізається
лише його фраза. Межі фраз ставимо тільки на початки тактів, які
збігаються з початком ноти мелодії. Усі фактури породжують ноти, що
починаються на offset'і ноти мелодії, тому жодна нота не перетинає межу.
"""

from __future__ import annotations

from typing import List, Sequence

from music21 import clef, layout, stream

from .model import ArrangeConfig, ArrangeContext
from .parsing import parse_input
from .assembly import build_hands, _assemble_part, tempo_mark


def phrase_bounds(ctx: ArrangeContext, bars_per_phrase: int = 4) -> List[float]:
    """Межі фраз як offset'и: [0, початок фрази 2, ..., нескінченність]."""
    bar_ql = ctx.ts.barDuration.quarterLength
    starts = {}
    for ev in ctx.events:
        if ctx.in_pickup(ev.offset):
            continue
        # подія мелодії, що стоїть рівно на тактовій риску
        if abs((ev.offset - ctx.pickup_ql) % bar_ql) < 1e-6:
            starts.setdefault(ev.measure, ev.offset)
    bounds = [0.0]
    for i, m in enumerate(sorted(starts)):
        if i > 0 and i % bars_per_phrase == 0:
            bounds.append(starts[m])
    bounds.append(float('inf'))
    return bounds


def describe_phrases(ctx: ArrangeContext, names: Sequence[str],
                     cfgs: Sequence[ArrangeConfig],
                     bars_per_phrase: int = 4) -> List[dict]:
    """План міксу як дані — для HTTP-відповіді: яка фраза якою фактурою і в яких тактах."""
    bar_ql = ctx.ts.barDuration.quarterLength
    bounds = phrase_bounds(ctx, bars_per_phrase)
    total = max(1, int(round((ctx.total_ql - ctx.pickup_ql) / bar_ql)))

    def bar_of(offset: float) -> int:
        return total + 1 if offset == float('inf') else int(round((offset - ctx.pickup_ql) / bar_ql)) + 1

    out = []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        slot = i % len(cfgs)
        out.append({'index': i + 1, 'preset': names[slot], 'name': cfgs[slot].name,
                    'from_bar': 1 if i == 0 else bar_of(lo),
                    'to_bar': max(bar_of(hi) - 1, 1 if i == 0 else bar_of(lo))})
    return out


def _slice(elems, lo: float, hi: float):
    return [el for el in elems if lo - 1e-6 <= el.offset < hi - 1e-6]


def arrange_mixed(source, cfgs: Sequence[ArrangeConfig],
                  bars_per_phrase: int = 4, verbose: bool = True) -> stream.Score:
    """Одна варіація, де фактури чергуються по фразах: cfgs[0], cfgs[1], ..."""
    ctx = parse_input(source)
    if any(c.neapolitan for c in cfgs):
        from .colors import add_neapolitan
        ctx = add_neapolitan(ctx, seed=cfgs[0].neapolitan_seed, verbose=verbose)
    bounds = phrase_bounds(ctx, bars_per_phrase)

    # кожну фактуру будуємо на весь гімн один раз, а не на кожну фразу
    built = {}

    rh_elems, lh_elems = [], []
    for i, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        slot = i % len(cfgs)
        cfg = cfgs[slot]
        if slot not in built:
            built[slot] = build_hands(ctx, cfg)
        rh, lh = built[slot]
        if isinstance(rh, tuple):
            raise ValueError(f"'{cfg.mode}' має два голоси — у міксі поки не підтримується")
        rh_elems += _slice(rh, lo, hi)
        lh_elems += _slice(lh, lo, hi)
        if verbose:
            end = 'кінець' if hi == float('inf') else hi
            print(f'  фраза {i + 1}: {lo} – {end}  ->  {cfg.name}')

    cfg0 = cfgs[0]
    rh_part = _assemble_part(rh_elems, ctx, clef.TrebleClef(),
                             'right-hand', 'Права рука', cfg0)
    lh_part = _assemble_part(lh_elems, ctx, clef.BassClef(),
                             'left-hand', 'Ліва рука', cfg0)
    rh_part.insert(0, tempo_mark(cfg0, ctx))

    sc = stream.Score()
    sc.insert(0, rh_part)
    sc.insert(0, lh_part)
    sc.insert(0, layout.StaffGroup([rh_part, lh_part], name='Баян',
                                   symbol='brace', barTogether=True))
    return sc
