"""Гармонічні барви: тимчасові відхилення, що повертаються в тональність.

Гармонія в рушії — це ДАНІ (ctx.chords), тож барва — це підміна одного
акорду в списку. Фактури нічого не знають про неї: вони просто беруть
акорд через ctx.chord_at() і обігрують те, що отримали.
"""

from __future__ import annotations

import random
from dataclasses import replace
from typing import List, Optional, Tuple

from music21 import harmony, key, pitch

from .model import ArrangeContext

# відстань від тоніки в півтонах
_PREDOMINANT = (2, 5)      # II / IV ступінь — їх і замінює N6
_DOMINANT = 7              # V ступінь


def _semis(tonic: pitch.Pitch, p: pitch.Pitch) -> int:
    return (p.pitchClass - tonic.pitchClass) % 12


def neapolitan_symbol(ctx: ArrangeContext) -> harmony.ChordSymbol:
    """N6: мажорний тризвук низького II ступеня, у басу — терція (IV ступінь)."""
    tonic = ctx.key.tonic
    root = tonic.transpose('m2')
    bass = tonic.transpose('P4')
    # бемоль у music21 — це '-': D-/F, а не Db/F
    return harmony.ChordSymbol(f'{root.name}/{bass.name}')


def _spans(ctx: ArrangeContext) -> List[Tuple[float, float, harmony.ChordSymbol]]:
    out = []
    for i, (off, cs) in enumerate(ctx.chords):
        end = ctx.chords[i + 1][0] if i + 1 < len(ctx.chords) else ctx.music_end_ql
        out.append((off, end, cs))
    return out


def neapolitan_candidates(ctx: ArrangeContext) -> List[int]:
    """
    Індекси акордів, які можна замінити на N6. Три правила:
      1. акорд — II або IV ступінь (субдомінантова функція);
      2. наступний акорд — теж субдомінанта або домінанта, НЕ тоніка:
         N6 має спасти в V, а не стрибнути додому;
      3. усі ноти мелодії, що звучать під акордом, — тони N6,
         інакше мелодія зіткнеться з низьким II ступенем.
    """
    tonic = ctx.key.tonic
    n6_pcs = {p.pitchClass for p in neapolitan_symbol(ctx).pitches}
    spans = _spans(ctx)
    out = []
    for i, (lo, hi, cs) in enumerate(spans[:-1]):
        if cs is None or ctx.in_pickup(lo):
            continue
        if _semis(tonic, cs.root()) not in _PREDOMINANT:
            continue
        nxt = spans[i + 1][2]
        if nxt is None or _semis(tonic, nxt.root()) not in _PREDOMINANT + (_DOMINANT,):
            continue
        mel = [e for e in ctx.events
               if not e.is_rest and e.offset < hi - 1e-6 and e.offset + e.ql > lo + 1e-6]
        if mel and all(e.pitch.pitchClass in n6_pcs for e in mel):
            out.append(i)
    return out


def add_neapolitan(ctx: ArrangeContext, seed: Optional[int] = None,
                   verbose: bool = False) -> ArrangeContext:
    """Повертає НОВИЙ контекст, де один придатний акорд замінено на N6."""
    cands = neapolitan_candidates(ctx)
    if not cands:
        if verbose:
            print('  N6: немає придатного місця — гармонію не змінено')
        return ctx
    i = random.Random(seed).choice(cands)
    lo, hi, old = _spans(ctx)[i]
    n6 = neapolitan_symbol(ctx)
    chords = list(ctx.chords)
    chords[i] = (lo, n6)
    # На час відхилення фігурація живе в тональності низького II ступеня
    # (у до мажорі — ре-бемоль мажор): допоміжні й прохідні беруться звідти,
    # інакше під D-/F звучали б мі та соль-бекар.
    local = list(ctx.local_keys) + [(lo, hi, key.Key(n6.root().name))]
    if verbose:
        print(f'  N6: {old.figure} на {lo} -> {n6.figure} (кандидатів: {len(cands)})')
    return replace(ctx, chords=chords, local_keys=local)
