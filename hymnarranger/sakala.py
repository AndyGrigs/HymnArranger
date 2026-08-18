"""Стиль баянної обробки за зразком Р. Сакали («Ах, радость»).

Наслідує ПРИНЦИПИ, зняті з нотного аналізу, а не копіює текст:

  1. Гармонія навмисно бідна — I, V, V7 покривають ~88% матеріалу.
     Багатший гармонізатор руйнує стиль.
  2. Ліва рука має один патерн на 71% тактів: Б А А Б А А.
     Єдина модифікація — терцієвий бас на 4-й долі й бас-зв'язка
     перед зміною гармонії. Квінтового басу немає взагалі.
  3. Варіація = ФАКТУРА + РЕГІСТР, а не нова гармонія.
  4. Октавна транспозиція тієї самої фігурації — повноцінна варіація
     (у джерелі т.22-24 і т.38-40 збігаються побітово зі зсувом +12).
  5. Уся хроматика зосереджена у зв'язках і коді, ніколи в темі.

Реалізовано наближено: строфа дорівнює довжині вхідного гімну, а не
фіксованим 16 тактам, і акорди беруться з розмітки, а не виводяться
аналізом. Зв'язка й кода будуються від тональності вхідного твору.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

from music21 import chord, harmony, key, note, pitch, stream

from .model import ArrangeContext, ArrangeConfig
from .theory import _step, _chord_tones_near, _clamp
from .meters import parts_for


# =================================================================
#  Озвучення кнопок Stradella
# =================================================================

def stradella_voicing(cs: harmony.ChordSymbol, lo: int = 55, hi: int = 68
                      ) -> List[pitch.Pitch]:
    """
    Готова система дає ФІКСОВАНІ тризвуки у вузькому діапазоні (G3–G4),
    без обернень. Тому тут не голосоведіння, а розкладка "як лягає рука":
    тони акорду підряд угору від нижньої межі.

    Домінантсептакорд звучить без квінти (D7 -> C D F#), а зменшений
    заміняє собою септакорд від чужого басу — це фізика інструмента,
    а не спрощення.
    """
    fig = (cs.figure or '').lower()
    names = [cs.root().name]
    if cs.third is not None:
        names.append(cs.third.name)
    if 'dim' in fig or '°' in fig:
        if cs.fifth is not None:
            names.append(cs.fifth.name)
    elif cs.seventh is not None and '7' in fig and 'maj7' not in fig:
        names.append(cs.seventh.name)          # квінта опускається
    elif cs.fifth is not None:
        names.append(cs.fifth.name)

    out = []
    for nm in dict.fromkeys(names):
        p = pitch.Pitch(nm)
        p.octave = 3
        while p.midi < lo:
            p = p.transpose(12)
        while p.midi > hi:
            p = p.transpose(-12)
        out.append(p)
    return sorted(out, key=lambda x: x.midi)


def build_left_hand(ctx: ArrangeContext, cfg: ArrangeConfig,
                    third_bass: bool = True) -> List[note.GeneralNote]:
    """
    Б А А | Б А А для 6/8 і будь-якого тридольного,
    Б А (А) для простих розмірів — тобто бас на 1-й і серединній долі.

    На другому басі — основний тон або ТЕРЦІЯ акорду (B під G, F# під D).
    Квінта не використовується: у джерелі її немає жодного разу.
    """
    ts = ctx.ts
    bar_ql = ts.barDuration.quarterLength
    beat = ts.beatDuration.quarterLength
    compound = abs(beat - 1.5) < 1e-6

    # Групи задаємо явно. Спроба вивести їх арифметикою давала для 3/4
    # чотири удари в тридольному такті — ліва рука перекривала сама себе.
    if compound:                      # 6/8, 9/8, 12/8 — групи по три вісімки
        unit, per_group = 0.5, 3
        groups = max(1, int(round(bar_ql / 1.5)))
    else:
        beats = max(1, int(round(bar_ql / beat)))
        unit = beat
        if beats % 2 == 0:            # 2/4, 4/4 -> Б А | Б А
            per_group, groups = 2, beats // 2
        else:                         # 3/4 -> Б А А (одна група на такт)
            per_group, groups = beats, 1

    out: List[note.GeneralNote] = []
    if ctx.pickup_ql > 1e-6:
        r = note.Rest(); r.duration.quarterLength = ctx.pickup_ql; r.offset = 0.0
        out.append(r)

    n_bars = max(1, int(round((ctx.total_ql - ctx.pickup_ql) / bar_ql)))
    for b in range(n_bars):
        bar_off = ctx.pickup_ql + b * bar_ql
        for g in range(groups):
            g_off = bar_off + g * unit * per_group
            cs = ctx.chord_at(g_off)
            if cs is None:
                r = note.Rest(); r.duration.quarterLength = unit * per_group
                r.offset = g_off; out.append(r)
                continue

            root = pitch.Pitch(cs.root().name); root.octave = 2
            if root.midi < 40:
                root = root.transpose(12)
            if g > 0 and third_bass and cs.third is not None:
                alt = pitch.Pitch(cs.third.name); alt.octave = root.octave
                if abs(alt.midi - root.midi) > 7:
                    alt = alt.transpose(-12 if alt.midi > root.midi else 12)
                bass = alt
            else:
                bass = root

            nb = note.Note(bass)
            nb.duration.quarterLength = unit
            nb.offset = g_off
            out.append(nb)

            voicing = stradella_voicing(cs)
            for j in range(1, per_group):
                c = chord.Chord([p.nameWithOctave for p in voicing])
                c.duration.quarterLength = unit
                c.offset = g_off + j * unit
                out.append(c)
    return out


# =================================================================
#  Фактури правої руки
# =================================================================

def _melody_at(ctx: ArrangeContext, off: float):
    for ev in ctx.events:
        if ev.offset <= off + 1e-6 < ev.offset + ev.ql and not ev.is_rest:
            return ev
    return None


def _parallel_below(p: pitch.Pitch, cs, k: key.Key) -> pitch.Pitch:
    """Нижній голос: терція або секста під мелодією, обов'язково в акорді."""
    for semis in (3, 4, 8, 9):
        cand = p.transpose(-semis)
        if cs is None or cand.pitchClass in {x.pitchClass for x in cs.pitches}:
            return cand
    return _step(_step(p, k, -1), k, -1)


def v0_thirds(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """V0 — тема двоголоссям: мелодія зверху, паралельний голос знизу."""
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            el = note.Rest()
        else:
            top = _clamp(ev.pitch.transpose(12 * cfg.octave_shift), cfg) \
                if cfg.octave_shift else ev.pitch
            low = _parallel_below(top, ctx.chord_at(ev.offset), ctx.key)
            el = chord.Chord([low.nameWithOctave, top.nameWithOctave])
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        out.append(el)
    return out


def v1_chords(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """V1 — акордизація: мелодія зверху, під нею повний тризвук."""
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            el = note.Rest()
        else:
            top = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
            cs = ctx.chord_at(ev.offset)
            below = [p for p in _chord_tones_near(cs, top) if p.midi < top.midi][-2:]
            el = chord.Chord([p.nameWithOctave for p in below] + [top.nameWithOctave])
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        out.append(el)
    return out


def v2_pedal(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    V2 — педальна фігурація, головний прийом стилю.

    Верхній двозвук (мелодія + терція/секста знизу) чергується з
    фіксованою нижньою нотою — педаллю на основному тоні акорду.
    Педаль не змінюється протягом усієї гармонії, тому фактура
    звучить як безперервний рух при статичному гармонічному тлі.
    """
    beat = ctx.ts.beatDuration.quarterLength
    n = parts_for(beat, cfg.arp_unit_ql, 12)
    n = max(2, n - n % 2)                      # парне: пара [двозвук, педаль]
    out = []
    off = 0.0
    while off < ctx.total_ql - 1e-6:
        ev = _melody_at(ctx, off)
        if ev is None or ctx.in_pickup(off):
            r = note.Rest(); r.duration.quarterLength = beat; r.offset = off
            out.append(r); off += beat; continue

        cs = ctx.chord_at(off)
        top = _clamp(ev.pitch.transpose(12 * cfg.octave_shift), cfg) \
            if cfg.octave_shift else ev.pitch
        low = _parallel_below(top, cs, ctx.key)
        ped = pitch.Pitch(cs.root().name) if cs is not None else pitch.Pitch(top.name)
        ped.octave = low.octave
        while ped.midi >= low.midi:
            ped = ped.transpose(-12)
        while low.midi - ped.midi > 12:
            ped = ped.transpose(12)

        sub = beat / n
        for j in range(n):
            if j % 2 == 0:
                el = chord.Chord([low.nameWithOctave, top.nameWithOctave])
            else:
                el = note.Note(pitch.Pitch(ped.nameWithOctave))
            el.duration.quarterLength = sub
            el.offset = off + j * sub
            out.append(el)
        off += beat
    return out


def v3_broken_sixths(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    V3 — ломані сексти й децими: чисте одноголосся зі стрибками.
    Нижня мелодична нота чергується з верхньою через сексту.
    """
    beat = ctx.ts.beatDuration.quarterLength
    n = parts_for(beat, cfg.arp_unit_ql, 12)
    n = max(2, n - n % 2)
    out = []
    off = 0.0
    while off < ctx.total_ql - 1e-6:
        ev = _melody_at(ctx, off)
        if ev is None or ctx.in_pickup(off):
            r = note.Rest(); r.duration.quarterLength = beat; r.offset = off
            out.append(r); off += beat; continue

        cs = ctx.chord_at(off)
        low = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
        # секста рахується ПО ГАМІ, а не в півтонах: механічні +9 давали
        # сі-бемоль у ре-мажорі, бо ця нота не входить у тонічний тризвук
        high = low
        for _ in range(5):
            high = _step(high, ctx.key, 1)
        if cs is not None:
            pcs = {x.pitchClass for x in cs.pitches}
            if high.pitchClass not in pcs:
                alt = _step(high, ctx.key, 1)     # децима замість сексти
                if alt.pitchClass in pcs:
                    high = alt

        sub = beat / n
        for j in range(n):
            raw = low if j % 2 == 0 else high
            el = note.Note(_clamp(pitch.Pitch(raw.nameWithOctave), cfg))
            el.duration.quarterLength = sub
            el.offset = off + j * sub
            out.append(el)
        off += beat
    return out


TEXTURES = {
    'V0': ('Тема двоголоссям', v0_thirds),
    'V1': ('Акордизація', v1_chords),
    'V2': ('Педальна фігурація', v2_pedal),
    'V3': ('Ломані сексти', v3_broken_sixths),
}


# =================================================================
#  Зв'язка і кода — єдині місця, де дозволена хроматика
# =================================================================

def link_chords(k: key.Key) -> List[Tuple[str, str]]:
    """
    Модуляційна ланка V/vi -> vi | V/V -> V7.

    У джерелі ця формула повторюється п'ять разів і завжди однакова —
    це єдиний хроматичний оборот у середині форми, який щоразу
    повертає до домінанти перед новою строфою.
    """
    t = k.tonic
    vi = t.transpose(9)
    return [
        (vi.transpose(7).name + '7', 'V/vi'),      # B7 у G-dur
        (vi.name + 'm', 'vi'),                     # Em
        (t.transpose(2).name + '7', 'V/V'),        # A7
        (t.transpose(7).name + '7', 'V7'),         # D7
    ]


def build_link(k: key.Key, ts, start_off: float) -> Tuple[list, list, float]:
    """Два такти зв'язки: права рука акордами, ліва — бас із кнопкою."""
    bar_ql = ts.barDuration.quarterLength
    beat = ts.beatDuration.quarterLength
    beats = max(1, int(round(bar_ql / beat)))
    # Тривалість акорду зв'язки — ЦІЛЕ число доль, а не половина такту:
    # у 9/8 половина такту дорівнює 2.25 і не нотується без ліги.
    per_chord = max(1, beats // 2) if beats >= 2 else 1
    rh, lh = [], []
    off = start_off
    for i, (fig, _deg) in enumerate(link_chords(k)):
        try:
            cs = harmony.ChordSymbol(fig)
        except Exception:
            continue
        dur = beat * per_chord
        tones = [p for p in _chord_tones_near(cs, pitch.Pitch('G4'))
                 if 60 <= p.midi <= 84][:3]
        if tones:
            c = chord.Chord([p.nameWithOctave for p in tones])
            c.duration.quarterLength = dur
            c.offset = off
            rh.append(c)
        b = pitch.Pitch(cs.root().name); b.octave = 2
        nb = note.Note(b); nb.duration.quarterLength = dur; nb.offset = off
        lh.append(nb)
        off += dur
    return rh, lh, off - start_off


def build_coda(k: key.Key, ts, start_off: float) -> Tuple[list, list, float]:
    """
    Кода: хроматично спадний бас від V до I, гармонізований
    паралельними зменшеними акордами в правій руці.

    Розмір не змінюємо на 3/8, як у джерелі: зміна метру всередині
    партитури зламала б сітку тактів, яку тримає решта пакета.
    Хроматичний спуск і розширення фактури зберігаються.
    """
    beat = ts.beatDuration.quarterLength
    t = k.tonic
    line = [t.transpose(7)]                        # від V
    for _ in range(6):
        line.append(line[-1].transpose(-1))        # хроматично вниз
    line.append(pitch.Pitch(t.name))               # до I

    rh, lh = [], []
    off = start_off
    for i, bp in enumerate(line):
        last = (i == len(line) - 1)
        dur = beat * (2 if last else 1)
        b = pitch.Pitch(bp.name); b.octave = 2
        nb = note.Note(b); nb.duration.quarterLength = dur; nb.offset = off
        lh.append(nb)

        if last:
            top = [pitch.Pitch(x.name) for x in
                   harmony.ChordSymbol(t.name + ('m' if k.mode == 'minor' else '')).pitches]
            voic = []
            for j, p in enumerate(top):
                q = pitch.Pitch(p.name); q.octave = 4 + (j // 3)
                voic.append(q)
            voic.append(pitch.Pitch(t.name + '5'))     # розширення фактури
        else:
            voic = [bp.transpose(n) for n in (12 + 3, 12 + 6, 12 + 9)]  # dim7
            voic = [pitch.Pitch(p.nameWithOctave) for p in voic]
            while voic and voic[0].midi < 60:
                voic = [p.transpose(12) for p in voic]
        c = chord.Chord([p.nameWithOctave for p in voic])
        c.duration.quarterLength = dur
        c.offset = off
        rh.append(c)
        off += dur
    return rh, lh, off - start_off


# =================================================================
#  План форми
# =================================================================

# Кожна строфа: (фактура, зсув октав, чи ставити зв'язку після)
DEFAULT_PLAN = [
    ('V0', 0, False),   # тема двоголоссям
    ('V1', 0, True),    # акордизація тієї ж теми
    ('V2', 0, True),    # педальна фігурація
    ('V2', 1, True),    # ВОНА Ж октавою вище — легітимна варіація стилю
    ('V3', 1, False),   # ломані сексти
]


def plan(n_strophes: int = 5, with_coda: bool = True) -> List[tuple]:
    p = DEFAULT_PLAN[:max(1, min(len(DEFAULT_PLAN), n_strophes))]
    if p and p[-1][2]:
        p[-1] = (p[-1][0], p[-1][1], False)
    return p


def describe(n_strophes: int = 5, with_coda: bool = True) -> List[dict]:
    """План як дані — для HTTP-відповіді й друку в CLI."""
    out = []
    for i, (tx, oct_, link) in enumerate(plan(n_strophes), start=1):
        out.append({'index': i, 'texture': tx, 'name': TEXTURES[tx][0],
                    'octave': oct_, 'link_after': link})
    if with_coda:
        out.append({'index': len(out) + 1, 'texture': 'CODA',
                    'name': 'Кода (хроматичний спуск)', 'octave': 0,
                    'link_after': False})
    return out


# =================================================================
#  Збірка
# =================================================================

def arrange_style(source, n_strophes: int = 5, with_coda: bool = True,
                  verbose: bool = True) -> stream.Score:
    """
    Повна обробка в стилі Сакали: строфи різної фактури, з'єднані
    хроматичною ланкою, з кодою наприкінці.

    Наслідування, а не копіювання: строфа дорівнює довжині вхідного
    гімну, гармонія береться з розмітки, розмір не змінюється в коді.
    """
    from .parsing import parse_input
    from .assembly import (make_instrument, tempo_mark, DEFAULT_TEMPO)
    from music21 import clef, expressions, bar as m21bar, layout, meter as m21meter

    ctx = parse_input(source)
    if verbose:
        for w in ctx.warnings:
            print('  [!] ' + w)
        print(f'  Стиль: обробка Сакали | {ctx.ts.ratioString} | {ctx.key}')

    bar_ql = ctx.ts.barDuration.quarterLength
    steps = plan(n_strophes, with_coda)

    rh_part = stream.Part(id='right-hand'); rh_part.partName = 'Права рука'
    lh_part = stream.Part(id='left-hand');  lh_part.partName = 'Ліва рука'
    for p, cl in ((rh_part, clef.TrebleClef()), (lh_part, clef.BassClef())):
        p.insert(0, make_instrument('Accordion'))
        p.insert(0, cl)
        p.insert(0, key.KeySignature(ctx.key.sharps))
        p.insert(0, m21meter.TimeSignature(ctx.ts.ratioString))

    cursor = 0.0
    marks = []
    tempos = {'V0': 84, 'V1': 88, 'V2': 96, 'V3': 100}

    for tx, oct_, link_after in steps:
        # стеля нижча за загальну: у джерелі кульмінація сягає D6,
        # а не краю клавіатури — верхній регістр тримається в резерві
        cfg = replace(ArrangeConfig(), octave_shift=oct_, arp_unit_ql=0.25,
                      rh_max_midi=89)
        rh_el = TEXTURES[tx][1](ctx, cfg)
        lh_el = build_left_hand(ctx, cfg)
        label = TEXTURES[tx][0] + (' (октавою вище)' if oct_ else '')
        marks.append((cursor, label, tempos.get(tx, DEFAULT_TEMPO)))
        for src, dst in ((rh_el, rh_part), (lh_el, lh_part)):
            for el in src:
                dst.insert(cursor + el.offset, el)
        cursor += ctx.total_ql

        if link_after:
            lrh, llh, span = build_link(ctx.key, ctx.ts, 0.0)
            marks.append((cursor, 'Зв\'язка', 92))
            span = max(span, bar_ql)
            for src, dst in ((lrh, rh_part), (llh, lh_part)):
                for el in src:
                    dst.insert(cursor + el.offset, el)
            n_bars = max(1, int(round(span / bar_ql + 0.49)))
            cursor += n_bars * bar_ql

    if with_coda:
        crh, clh, span = build_coda(ctx.key, ctx.ts, 0.0)
        marks.append((cursor, 'Кода', 76))
        for src, dst in ((crh, rh_part), (clh, lh_part)):
            for el in src:
                dst.insert(cursor + el.offset, el)
        cursor += max(1, int(round(span / bar_ql + 0.49))) * bar_ql

    for p in (rh_part, lh_part):
        p.makeNotation(inPlace=True)
        for i, m in enumerate(p.getElementsByClass(stream.Measure), start=1):
            m.number = i

    ms = list(rh_part.getElementsByClass(stream.Measure))
    for off, label, tmp in marks:
        hit = [m for m in ms if abs(m.offset - off) < 1e-6]
        if hit:
            hit[0].insert(0, expressions.RehearsalMark(label))
            hit[0].insert(0, tempo_mark(replace(ArrangeConfig(), tempo=tmp), ctx))
    if ms:
        ms[-1].rightBarline = m21bar.Barline('final')
    lms = list(lh_part.getElementsByClass(stream.Measure))
    if lms:
        lms[-1].rightBarline = m21bar.Barline('final')

    sc = stream.Score()
    sc.insert(0, rh_part)
    sc.insert(0, lh_part)
    sc.insert(0, layout.StaffGroup([rh_part, lh_part], name='Баян',
                                   symbol='brace', barTogether=True))
    if verbose:
        for _, label, tmp in marks:
            print(f'    {label} (♩={tmp})')
    return sc