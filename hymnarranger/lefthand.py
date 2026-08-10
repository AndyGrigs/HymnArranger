"""Ліва рука: озвучення кнопок готового баса і голосоведіння.

Патерни (яка доля — бас, яка — акорд) живуть у meters/, бо саме
вони залежать від розміру. Тут — тільки те, ЯК звучить акорд.
"""

from __future__ import annotations

from typing import Optional, List

from music21 import chord, harmony, key, meter, note, pitch

from .model import ArrangeContext, ArrangeConfig
from .meters import lh_pattern_for


def _stradella_names(cs: harmony.ChordSymbol) -> List[str]:
    """
    Реальне звучання акордової кнопки готового баса.
    Виправляє баг v1: там прима взагалі не потрапляла в акорд.
    Мажор/мінор -> прима+терція+квінта. Домінантсептакорд -> прима+терція+септима
    (квінта опускається — так влаштована кнопка). Зменшений -> прима+м3+зм5.
    """
    fig = (cs.figure or '').lower()
    root, third, fifth, seventh = cs.root(), cs.third, cs.fifth, cs.seventh
    names = [root.name]
    if 'dim' in fig or '°' in fig:
        if third: names.append(third.name)
        if fifth: names.append(fifth.name)
    elif seventh is not None and ('7' in fig) and 'maj7' not in fig:
        if third: names.append(third.name)
        names.append(seventh.name)
    else:
        if third: names.append(third.name)
        if fifth: names.append(fifth.name)

    return list(dict.fromkeys(names))


def _stradella_voicing_fixed(names: List[str], octv: int) -> List[pitch.Pitch]:
    """Основний вигляд у заданій октаві (запасний варіант і режим без голосоведіння)."""
    out, prev = [], None
    for nm in names:
        p = pitch.Pitch(nm)
        p.octave = octv
        if prev is not None and p.midi <= prev.midi:
            p.octave += 1                      # тісне розташування, вгору
        out.append(p)
        prev = p
    return out


def _voicing_candidates(names: List[str], cfg: ArrangeConfig) -> List[List[pitch.Pitch]]:
    """Усі обернення акорду в тісному розташуванні, чия нижня нота
    вкладається у дозволений регістр лівої руки."""
    n = len(names)
    cands = []
    for rot in range(n):
        order = names[rot:] + names[:rot]
        for base_oct in range(2, 6):
            voicing, prev = [], None
            for nm in order:
                p = pitch.Pitch(nm)
                p.octave = base_oct
                if prev is not None and p.midi <= prev.midi:
                    p.octave += 1
                voicing.append(p)
                prev = p
            if cfg.lh_chord_lo_midi <= voicing[0].midi <= cfg.lh_chord_hi_midi:
                cands.append(voicing)
    return cands


def _closest_voicing(names: List[str], prev: Optional[List[pitch.Pitch]],
                     cfg: ArrangeConfig) -> List[pitch.Pitch]:
    """
    Обирає обернення з найменшим сумарним рухом голосів відносно
    попереднього акорду. Це те, що робить рука музиканта: не стрибає
    в основний вигляд щоразу, а йде найкоротшим шляхом.
    """
    cands = _voicing_candidates(names, cfg)
    if not cands:
        return _stradella_voicing_fixed(names, cfg.lh_chord_octave)
    if prev is None:
        # перший акорд твору — основний вигляд: він встановлює тональність
        return _stradella_voicing_fixed(names, cfg.lh_chord_octave)

    def cost(v):
        m = min(len(v), len(prev))
        moved = sum(abs(v[i].midi - prev[i].midi) for i in range(m))
        return moved + 2 * abs(len(v) - len(prev))
    return min(cands, key=cost)


def build_left_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    Ліва рука, побудована ПО ТАКТАХ (а не по спанах акордів, як у v1).
    Саме це гарантує, що ліва рука має ту саму довжину, що й права.
    """
    bar_ql = ctx.ts.barDuration.quarterLength
    beat_ql, pattern = lh_pattern_for(ctx.ts, cfg)
    prev_voicing: Optional[List[pitch.Pitch]] = None
    out: List[note.GeneralNote] = []

    if ctx.pickup_ql > 1e-6:                 # затакт ліва рука мовчить
        r = note.Rest(); r.duration.quarterLength = ctx.pickup_ql; r.offset = 0.0
        out.append(r)

    n_bars = max(1, int(round((ctx.total_ql - ctx.pickup_ql) / bar_ql)))
    for bar in range(n_bars):
        bar_off = ctx.pickup_ql + bar * bar_ql
        for i, role in enumerate(pattern):
            off = bar_off + i * beat_ql
            if off >= ctx.total_ql - 1e-6:
                break
            cs = ctx.chord_at(off)
            if ctx.in_pickup(off) or cs is None:
                r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = off
                out.append(r)
                continue

            if role in ('B', 'F'):
                if role == 'F' and not cfg.alt_bass_on_change:
                    prev = ctx.chord_at(off - beat_ql) if off >= beat_ql else None
                    if prev is None or prev.figure != cs.figure:
                        role = 'B'          # акорд щойно змінився -> прима
                root = pitch.Pitch(cs.root().name)
                root.octave = cfg.lh_bass_octave
                if role == 'B':
                    p = root
                else:
                    # На баяні допоміжний бас лежить у тому ж ряду ВИЩЕ
                    # основного, тому це завжди чиста квінта вгору,
                    # а не той самий тон у другій октаві:
                    #   F2 -> C3, C2 -> G2, G2 -> D3
                    p = root.transpose(7)
                    if cs.fifth is not None and p.pitchClass != cs.fifth.pitchClass:
                        p = pitch.Pitch(cs.fifth.name)
                        p.octave = root.octave
                        if p.midi <= root.midi:
                            p.octave += 1
                el = note.Note(p)
            else:
                names = _stradella_names(cs)
                if cfg.lh_voice_leading:
                    voicing = _closest_voicing(names, prev_voicing, cfg)
                    prev_voicing = voicing
                else:
                    voicing = _stradella_voicing_fixed(names, cfg.lh_chord_octave)
                el = chord.Chord([p.nameWithOctave for p in voicing])
            el.duration.quarterLength = beat_ql
            el.offset = off
            out.append(el)
    return out
