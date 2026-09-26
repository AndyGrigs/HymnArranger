"""Ліва рука: озвучення кнопок готового баса і голосоведіння.

Патерни (яка доля — бас, яка — акорд) живуть у meters/, бо саме
вони залежать від розміру. Тут — тільки те, ЯК звучить акорд.
"""

from __future__ import annotations

import math

from typing import List, Optional, Tuple

from music21 import chord, harmony, note, pitch

from .model import ArrangeContext, ArrangeConfig
from .sakala import stradella_voicing


#: Октава прими ходової лінії (I -> III -> V). Терція й квінта лягають
#: найближче ВГОРУ від прими в цій-таки октаві.
_BASS_OCTAVE = 3


def _cs_id(cs: harmony.ChordSymbol) -> str:
    """Стабільний ідентифікатор гармонії — щоб відрізнити зміну акорду
    від повторення того самого (порівнюємо `figure`, а не сам об'єкт)."""
    return cs.figure or ''


def _bass_degree(cs: harmony.ChordSymbol, degree: int) -> pitch.Pitch:
    """Прима/терція/квінта акорду (`degree` 0/1/2) для ходової басової лінії.

    Терція й квінта лежать найближче ВГОРУ від прими: та сама октава, якщо
    вона там і так вища за приму, інакше октавою вище — так лінія рухається
    компактно (терція чи кварта вгору), а не стрибає невизначено. Якщо
    в акорді немає терції чи квінти (напр., sus без квінти), підміняємо
    примою — краще повторити приму, ніж мовчати чи брати чужий тон.
    """
    root = pitch.Pitch(cs.root().name)
    root.octave = _BASS_OCTAVE
    if degree % 3 == 0:
        return root

    tone = cs.third if degree % 3 == 1 else cs.fifth
    if tone is None:
        return root

    p = pitch.Pitch(tone.name)
    p.octave = _BASS_OCTAVE
    if p.midi <= root.midi:
        p.octave += 1
    return p


def build_left_hand(ctx: ArrangeContext, cfg: ArrangeConfig,
                    cycle: Tuple[int, ...] = (0, 1, 2)
                    ) -> List[note.GeneralNote]:
    """
    Ліва рука: ходовий бас вісімками по ступенях акорду I -> III -> V,
    а між ними — акорд Stradella.

    Одиниця руху — вісімка в БУДЬ-ЯКОМУ розмірі. Відрізняється тільки
    довжина групи:
      складені (3/8, 6/8, 9/8, 12/8) -> Б А А, бас на кожну третю вісімку;
      прості  (2/4, 3/4, 4/4, 12/4)  -> Б А,   бас на кожну другу.
    Ознака складеності — `beatDuration` 1.5: music21 дає її і для 3/8,
    тож окремий перелік розмірів не потрібен.

    Лічильник циклу СКИДАЄТЬСЯ на кожній зміні гармонії: нова функція
    завжди входить примою, інакше слух не чує, де саме мінявся акорд,
    і басова лінія перетворюється на безадресний рух.

    Межа `ctx.music_end_ql` (а не `ctx.total_ql`) — щоб довжина лівої руки
    збігалася з правою: `total_ql` округлений угору до тактової сітки і
    в творі із затактом більший за фактичний кінець мелодії.

    Дужкові баси з оригінального видання не відтворюються: це редакторська
    позначка натиснутої кнопки, а не окрема атака.
    """
    ts = ctx.ts
    bar_ql = ts.barDuration.quarterLength
    compound = abs(ts.beatDuration.quarterLength - 1.5) < 1e-6
    unit = 0.5
    per_group = 3 if compound else 2
    n_slots = max(1, int(round(bar_ql / unit)))

    out: List[note.GeneralNote] = []
    if ctx.pickup_ql > 1e-6:
        r = note.Rest(); r.duration.quarterLength = ctx.pickup_ql; r.offset = 0.0
        out.append(r)

    _end = ctx.music_end_ql
    n_bars = max(1, math.ceil((_end - ctx.pickup_ql) / bar_ql - 1e-6))
    prev_id: Optional[str] = None
    step_i = 0

    for b in range(n_bars):
        bar_off = ctx.pickup_ql + b * bar_ql
        for i in range(n_slots):
            off = bar_off + i * unit
            if off >= _end - 1e-6:
                break
            cs = ctx.chord_at(off)
            if cs is None:
                r = note.Rest(); r.duration.quarterLength = unit
                r.offset = off; out.append(r)
                continue

            if i % per_group == 0:
                cid = _cs_id(cs)
                if cid != prev_id:
                    step_i = 0
                    prev_id = cid
                el = note.Note(_bass_degree(cs, cycle[step_i % len(cycle)]))
                step_i += 1
            else:
                el = chord.Chord([q.nameWithOctave
                                  for q in stradella_voicing(cs)])
            el.duration.quarterLength = unit
            el.offset = off
            out.append(el)
    return out
