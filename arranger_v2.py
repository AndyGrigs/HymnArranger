
"""
arranger.py v2 — генератор баянної партитури з мелодії + акордових символів.

Архітектура (3 шари):
    1. ПАРСЕР        MusicXML -> ArrangeContext (абсолютні offset'и, гарм. сітка)
    2. РУШІЙ         ArrangeContext + ArrangeConfig -> списки нот (RH / LH)
    3. СКЛАДАЛЬНИК   списки нот -> Score з тактами, ключами, StaffGroup -> MusicXML

Залежність: music21
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from music21 import (
    stream, note, chord, harmony, key, meter, clef,
    pitch, converter, layout, tempo, expressions,
)

# =================================================================
#  ШАР 1. ПРОМІЖНА МОДЕЛЬ І ПАРСЕР
# =================================================================


@dataclass
class MelodyEvent:
    """Одна подія мелодії з АБСОЛЮТНИМ offset'ом у партитурі."""
    offset: float               # абсолютний offset у чвертях від початку
    ql: float                   # тривалість у чвертях
    pitch: Optional[pitch.Pitch]  # None => пауза
    measure: int                # номер такту
    beat: float                 # доля всередині такту, 1.0 = перша

    @property
    def is_rest(self) -> bool:
        return self.pitch is None


CHORD_RE = re.compile(
    r'^([A-Ha-h])([#♯b♭\-]?)'          # основний тон (+ H/B німецькою)
    r'(m|min|maj|dim|aug|°|\+|M)?'      # лад
    r'(\d*)'                            # 7, 9, 6, 11, 13
    r'(sus[24]?|add\d+)?'               # sus / add
    r'(?:/([A-Ha-h][#♯b♭\-]?))?$'       # басова нота (слеш-акорд)
)


def text_to_chord_symbol(txt: str, german: bool = False) -> Optional[harmony.ChordSymbol]:
    """
    Перетворює текстовий підпис ('Am', 'H7', 'Bb', 'F#m/A') на ChordSymbol.

    УВАГА про 'B': у німецькій/українській традиції B = сі-бемоль, H = сі-бекар;
    в англо-американській B = сі-бекар. Різниця в півтон, і помилка тиха.
    Тому інтерпретація 'B' керується прапорцем german, який визначається
    автоматично за наявністю 'H' у файлі.
    """
    if not txt:
        return None
    t = txt.strip().replace('♭', 'b').replace('♯', '#')
    if t.upper() in ('N.C.', 'NC', 'N.C', '-', '—'):
        return None
    m = CHORD_RE.match(t)
    if not m:
        return None

    def norm_root(letter: str, acc: str) -> str:
        L = letter.upper()
        if L == 'H':                       # H однозначно = сі-бекар
            return 'B'
        if L == 'B' and acc == '' and german:
            return 'B-'                    # тільки в німецькому режимі
        return L + acc.replace('b', '-')

    root, acc, qual, num, ext, bass = m.groups()
    fig = norm_root(root, acc or '')
    if qual in ('m', 'min'):
        fig += 'm'
    elif qual in ('maj', 'M'):
        fig += 'maj'
    elif qual:
        fig += {'dim': 'dim', '°': 'dim', 'aug': '+', '+': '+'}.get(qual, '')
    fig += (num or '') + (ext or '')
    if bass:
        fig += '/' + norm_root(bass[0], bass[1:] or '')
    try:
        return harmony.ChordSymbol(fig)
    except Exception:
        return None


@dataclass
class ArrangeContext:
    """Все, що рушій має знати про вхідну мелодію."""
    events: List[MelodyEvent]
    chords: List[Tuple[float, harmony.ChordSymbol]]   # відсортовано за offset
    key: key.Key
    ts: meter.TimeSignature
    total_ql: float
    warnings: List[str] = field(default_factory=list)
    chord_source: str = 'harmony'        # 'harmony' | 'text' | 'lyrics' | 'none'

    def chord_at(self, offset: float) -> Optional[harmony.ChordSymbol]:
        """Акорд, що діє на заданому АБСОЛЮТНОМУ offset."""
        active = None
        for off, cs in self.chords:
            if off <= offset + 1e-6:
                active = cs
            else:
                break
        return active

    def next_sounding_pitch(self, idx: int) -> Optional[pitch.Pitch]:
        """Висота наступної не-паузи після події idx."""
        for ev in self.events[idx + 1:]:
            if not ev.is_rest:
                return ev.pitch
        return None


def parse_input(source) -> ArrangeContext:
    """
    Читає MusicXML (шлях, рядок або готовий Stream) і будує ArrangeContext
    з АБСОЛЮТНИМИ offset'ами. Це виправляє головний баг v1: після recurse()
    offset ноти був відносним до свого такту.
    """
    if isinstance(source, stream.Stream):
        sc = source
    else:
        sc = converter.parse(source)

    part = sc.parts[0] if getattr(sc, 'parts', None) else sc

    # --- тональність: спершу з файлу, лише потім аналіз ---
    ks = part.recurse().getElementsByClass(key.KeySignature).first()
    if isinstance(ks, key.Key):
        k = ks
    elif ks is not None:
        k = ks.asKey('major')
    else:
        k = part.analyze('key')

    ts = (part.recurse().getElementsByClass(meter.TimeSignature).first()
          or meter.TimeSignature('4/4'))
    bar_ql = ts.barDuration.quarterLength

    events: List[MelodyEvent] = []
    chords: List[Tuple[float, harmony.ChordSymbol]] = []

    measures = list(part.getElementsByClass(stream.Measure))

    if measures:
        for m in measures:
            m_off = m.offset
            m_num = m.number
            for el in m.notesAndRests:
                abs_off = m_off + el.offset
                if isinstance(el, harmony.ChordSymbol):
                    chords.append((abs_off, el))
                    continue
                p = None if el.isRest else el.pitches[-1]  # верхній голос = мелодія
                events.append(MelodyEvent(
                    offset=abs_off,
                    ql=el.duration.quarterLength,
                    pitch=p,
                    measure=m_num,
                    beat=(el.offset % bar_ql) + 1.0,
                ))
            # ChordSymbol може лежати поза notesAndRests у деяких експортерах
            for cs in m.getElementsByClass(harmony.ChordSymbol):
                pair = (m_off + cs.offset, cs)
                if pair not in chords:
                    chords.append(pair)
    else:
        flat = part.flatten()
        for el in flat.notesAndRests:
            if isinstance(el, harmony.ChordSymbol):
                chords.append((el.offset, el))
                continue
            p = None if el.isRest else el.pitches[-1]
            events.append(MelodyEvent(
                offset=el.offset,
                ql=el.duration.quarterLength,
                pitch=p,
                measure=int(el.offset // bar_ql) + 1,
                beat=(el.offset % bar_ql) + 1.0,
            ))

    events.sort(key=lambda e: e.offset)
    # дедуплікація акордів на однаковому offset (лишаємо перший)
    seen, uniq = set(), []
    for off, cs in sorted(chords, key=lambda x: x[0]):
        ro = round(off, 4)
        if ro not in seen:
            seen.add(ro)
            uniq.append((off, cs))

    total = max((e.offset + e.ql for e in events), default=0.0)
    # округлюємо до цілих тактів
    if total % bar_ql > 1e-6:
        total = (int(total // bar_ql) + 1) * bar_ql

    warns: List[str] = []
    source = 'harmony'

    # --- РЕЗЕРВ 1: акорди набрані як текст над нотами (Staff/System Text) ---
    if not uniq:
        texts = [(te.getOffsetInHierarchy(part), (te.content or '').strip())
                 for te in part.recurse().getElementsByClass(expressions.TextExpression)]
        german = any(t[:1].upper() == 'H' and text_to_chord_symbol(t) is not None
                     for _, t in texts)
        found = []
        for off, t in texts:
            cs = text_to_chord_symbol(t, german=german)
            if cs is not None:
                found.append((off, cs))
        if found and german:
            warns.append('Виявлено H -> німецьке позначення: B читається як сі-бемоль.')
        if found:
            uniq, source = sorted(found, key=lambda x: x[0]), 'text'
            warns.append(
                f'Акорди прочитано з ТЕКСТУ ({len(uniq)} шт.), а не з Chord Symbols. '
                'Працює, але надійніше набирати їх як акордові символи (Ctrl+K).')

    # --- РЕЗЕРВ 2: акорди в підспівці (lyrics) ---
    if not uniq:
        found = []
        for m in (measures or [part]):
            for el in m.notes:
                if el.lyric:
                    cs = text_to_chord_symbol(el.lyric)
                    if cs is not None:
                        found.append((m.offset + el.offset if measures else el.offset, cs))
        if found:
            uniq, source = sorted(found, key=lambda x: x[0]), 'lyrics'
            warns.append(f'Акорди прочитано з ПІДСПІВКИ ({len(uniq)} шт.).')

    # --- ДІАГНОСТИКА ---
    if not uniq:
        source = 'none'
        warns.append(
            'АКОРДІВ НЕ ЗНАЙДЕНО. Ліва рука буде порожня. У MuseScore/Flat.io '
            'акорд додається як Chord Symbol (Ctrl+K), а не як текст над нотою.')
    else:
        if uniq[0][0] > 1e-6:
            warns.append(f'Перший акорд аж на offset {uniq[0][0]} — початок без гармонії.')
        n_bars = max(1, int(round(total / bar_ql)))
        empty = [b + 1 for b in range(n_bars)
                 if not any(abs(o - b * bar_ql) < bar_ql and o <= b * bar_ql + 1e-6
                            for o, _ in uniq)]
        bare = [b for b in empty if b == 1]
        if bare:
            warns.append(f'Такти без активної гармонії: {bare}')

    return ArrangeContext(events=events, chords=uniq, key=k, ts=ts,
                          total_ql=total, warnings=warns, chord_source=source)


# =================================================================
#  ШАР 2a. ДІАТОНІЧНІ ПРИМІТИВИ
# =================================================================


def _step(p: pitch.Pitch, k: key.Key, direction: int) -> pitch.Pitch:
    """Сусідній діатонічний ступінь тональності вгору (+1) чи вниз (-1)."""
    # УВАГА: k.next() — це успадкований Music21Object.next() (навігація по
    # потоку), він кидає виняток. Діатонічний крок дає саме nextPitch()
    # з ЧИСЛОВИМ напрямком.
    try:
        res = k.nextPitch(p, 1 if direction > 0 else -1)
    except Exception:
        res = None
    if res is None:
        res = p.transpose(2 * direction)
    return pitch.Pitch(res.nameWithOctave)


def _steps_between(p1: pitch.Pitch, p2: pitch.Pitch, k: key.Key, cap: int = 10) -> int:
    """Скільки діатонічних кроків від p1 до p2 (знак = напрямок)."""
    if p1.midi == p2.midi:
        return 0
    direction = 1 if p2.midi > p1.midi else -1
    cur, n = p1, 0
    while n < cap:
        cur = _step(cur, k, direction)
        n += 1
        if (direction > 0 and cur.midi >= p2.midi) or (direction < 0 and cur.midi <= p2.midi):
            break
    return n * direction


def _chord_tones_near(cs: Optional[harmony.ChordSymbol],
                      ref: pitch.Pitch) -> List[pitch.Pitch]:
    """
    Тони акорду, перекладені в регістр навколо ref (± октава).
    Виправляє баг v1: ChordSymbol.pitches за замовчуванням лежить в 3-й октаві,
    тобто нижче мелодії, і фільтр "вище мелодії" давав порожній список.
    """
    if cs is None:
        return []
    out = []
    for p in cs.pitches:
        for octv in (ref.octave - 1, ref.octave, ref.octave + 1):
            q = pitch.Pitch(p.name)
            q.octave = octv
            out.append(q)
    return sorted(set(out), key=lambda x: x.midi)


def _nearest_chord_tone(cs, ref: pitch.Pitch, direction: int,
                        k: key.Key) -> pitch.Pitch:
    """Найближчий тон акорду вище (+1) або нижче (-1) від ref."""
    cands = _chord_tones_near(cs, ref)
    if direction > 0:
        cands = [p for p in cands if p.midi > ref.midi]
        return cands[0] if cands else _step(ref, k, 1)
    cands = [p for p in cands if p.midi < ref.midi]
    return cands[-1] if cands else _step(ref, k, -1)


def _chord_tone_between(cs, p1: pitch.Pitch, p2: pitch.Pitch,
                        k: key.Key) -> pitch.Pitch:
    """Тон акорду строго між p1 і p2, найближчий до середини стрибка."""
    lo, hi = min(p1.midi, p2.midi), max(p1.midi, p2.midi)
    mid = (lo + hi) / 2
    cands = [p for p in _chord_tones_near(cs, p1) if lo < p.midi < hi]
    if cands:
        return min(cands, key=lambda p: abs(p.midi - mid))
    return _step(p1, k, 1 if p2.midi > p1.midi else -1)


def _approach_tone(target: pitch.Pitch, from_side: pitch.Pitch,
                   k: key.Key) -> pitch.Pitch:
    """Ввідний тон до target з боку from_side. Ніколи не дорівнює target."""
    if target.midi == from_side.midi:
        return _step(target, k, -1)
    return _step(target, k, -1 if from_side.midi < target.midi else 1)


# =================================================================
#  ШАР 2b. КОНФІГ І РУШІЙ ФІГУРАЦІЇ
# =================================================================


SECOND_STRATEGIES = ('chord_tone', 'neighbor_away')
LH_PATTERNS = ('bass_chord', 'bass_alt_fifth', 'waltz', 'auto')


@dataclass
class ArrangeConfig:
    """Один об'єкт = один стиль аранжування. Новий стиль != новий цикл коду."""
    subdivision: int = 2                 # 2 = вісімки, 4 = шістнадцяті
    cadence_subdivision: Optional[int] = None   # дрібніше на останній ноті такту
    min_ql_to_split: float = 1.0         # дробимо ноти від чверті й довші
    second_strategy: str = 'chord_tone'  # як розв'язувати "впирання" в секунду
    tight_figure: str = 'neighbor'       # 'neighbor' (оспівування) | 'arpeggio'
    lh_pattern: str = 'auto'
    lh_bass_octave: int = 2
    lh_chord_octave: int = 3
    rh_min_midi: int = 53                # F3 — низ правої клавіатури баяна
    rh_max_midi: int = 96                # C7
    name: str = 'default'


def _clamp(p: pitch.Pitch, cfg: ArrangeConfig) -> pitch.Pitch:
    while p.midi < cfg.rh_min_midi:
        p = p.transpose(12)
    while p.midi > cfg.rh_max_midi:
        p = p.transpose(-12)
    return p


def figurate(cur: pitch.Pitch, target: Optional[pitch.Pitch],
             cs, k: key.Key, n_parts: int, cfg: ArrangeConfig) -> List[pitch.Pitch]:
    """
    ЯДРО СИСТЕМИ. Повертає рівно n_parts висот для однієї ноти мелодії.
    Інваріант: slot 0 ЗАВЖДИ = нота мелодії (сильна доля недоторкана).
    Інваріант: жоден слот не дорівнює target (немає передчасного дублювання).
    """
    if n_parts <= 1:
        return [cur]

    if target is None:                       # кінець фрази — обіграємо на місці
        target = _nearest_chord_tone(cs, cur, -1, k)

    diff = target.midi - cur.midi
    steps = abs(_steps_between(cur, target, k))

    if n_parts == 2:
        if diff == 0:                                    # повтор ноти
            fill = _step(cur, k, -1)
        elif steps <= 1:                                 # СЕКУНДА — спірний випадок
            if cfg.second_strategy == 'chord_tone':
                fill = _nearest_chord_tone(cs, cur, -1, k)
            else:                                        # neighbor_away
                fill = _step(cur, k, -1 if diff > 0 else 1)
        elif steps == 2:                                 # терція -> прохідний тон
            fill = _step(cur, k, 1 if diff > 0 else -1)
        else:                                            # стрибок -> тон акорду всередині
            fill = _chord_tone_between(cs, cur, target, k)
        if fill.midi == target.midi:                     # страхівка від дублювання
            fill = _step(cur, k, -1 if diff > 0 else 1)
        return [cur, _clamp(fill, cfg)]

    # --- n_parts >= 3: [мелодія, заповнення..., ввідний тон] ---
    approach = _approach_tone(target, cur, k)
    n_fill = n_parts - 2
    fill: List[pitch.Pitch] = []

    fill_steps = abs(_steps_between(cur, approach, k))
    if fill_steps >= n_fill + 1:
        # достатньо місця для гамоподібного руху
        direction = 1 if approach.midi > cur.midi else -1
        p = cur
        for _ in range(n_fill):
            p = _step(p, k, direction)
            fill.append(p)
    elif cfg.tight_figure == 'neighbor':
        # ОСПІВУВАННЯ: cur -> допоміжний з протилежного від цілі боку -> cur ...
        # Дає плавний хоральний рух замість октавних стрибків.
        away = _step(cur, k, -1 if target.midi > cur.midi else 1)
        cycle = [away, cur]
        fill = [cycle[i % 2] for i in range(n_fill)]
    else:
        # АРПЕДЖІО: розкладаємо акорд навколо мелодії (яскравіше, віртуозніше)
        near = [p for p in _chord_tones_near(cs, cur) if p.midi != target.midi]
        up = [p for p in near if p.midi > cur.midi]
        down = [p for p in near if p.midi < cur.midi]
        pool = (up[:2] + down[::-1][:2]) or [_step(cur, k, 1), _step(cur, k, -1)]
        i = 0
        while len(fill) < n_fill:
            fill.append(pool[i % len(pool)])
            i += 1

    figure = [cur] + fill + [approach]
    figure = [f if f.midi != target.midi else _step(f, k, -1) for f in figure]
    figure[0] = cur                                       # інваріант сильної долі
    return [_clamp(p, cfg) for p in figure]


def build_right_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """Права рука: мелодія з фігурацією. Повертає ноти з абсолютними offset'ами."""
    bar_ql = ctx.ts.barDuration.quarterLength
    # останні звучні ноти кожного такту — для каденційного дроблення
    last_in_measure = {}
    for ev in ctx.events:
        if not ev.is_rest:
            last_in_measure[ev.measure] = ev.offset

    out: List[note.GeneralNote] = []
    for i, ev in enumerate(ctx.events):
        if ev.is_rest:
            r = note.Rest()
            r.duration.quarterLength = ev.ql
            r.offset = ev.offset
            out.append(r)
            continue

        n_parts = 1
        if ev.ql >= cfg.min_ql_to_split:
            n_parts = cfg.subdivision
            if (cfg.cadence_subdivision
                    and last_in_measure.get(ev.measure) == ev.offset):
                n_parts = cfg.cadence_subdivision

        if n_parts <= 1:
            n = note.Note(ev.pitch)
            n.duration.quarterLength = ev.ql
            n.offset = ev.offset
            out.append(n)
            continue

        cs = ctx.chord_at(ev.offset)
        target = ctx.next_sounding_pitch(i)
        pitches = figurate(ev.pitch, target, cs, ctx.key, n_parts, cfg)
        sub = ev.ql / n_parts
        for j, p in enumerate(pitches):
            n = note.Note(p)
            n.duration.quarterLength = sub
            n.offset = ev.offset + j * sub
            out.append(n)
    return out


# ---------------- ліва рука: Stradella ----------------

def _stradella_voicing(cs: harmony.ChordSymbol, octv: int) -> List[pitch.Pitch]:
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

    out, prev = [], None
    for nm in dict.fromkeys(names):
        p = pitch.Pitch(nm)
        p.octave = octv
        if prev is not None and p.midi <= prev.midi:
            p.octave += 1                      # тісне розташування, вгору
        out.append(p)
        prev = p
    return out


def _lh_pattern_for(ts: meter.TimeSignature, cfg: ArrangeConfig) -> Tuple[float, List[str]]:
    """
    (тривалість одного удару, послідовність 'B'/'F'/'A' на ОДИН такт).
    Інваріант: beat_ql * len(pattern) == довжина такту. Інакше ліва рука
    "поїде" відносно правої — саме це й ламало пресет 'waltz' у 4/4.
    """
    num, den = ts.numerator, ts.denominator
    bar_ql = ts.barDuration.quarterLength
    p = cfg.lh_pattern

    if den == 8 and num % 3 == 0:                       # 6/8, 9/8, 12/8
        groups = num // 3
        pat = []
        for g in range(groups):
            pat += ['B' if g % 2 == 0 else 'F', 'A', 'A']
        cand = (0.5, pat)
    elif num == 3:                                      # вальсова тридольність
        cand = (bar_ql / 3, ['B', 'A', 'A'])
    elif num == 2:
        cand = (bar_ql / 2, ['B', 'A'])
    elif p == 'bass_chord':
        cand = (bar_ql / 4, ['B', 'A', 'B', 'A'])
    else:                                               # auto / bass_alt_fifth
        cand = (bar_ql / 4, ['B', 'A', 'F', 'A'])

    # явний вибір користувача — тільки якщо він розміру не суперечить
    if p == 'waltz' and num != 3:
        pass                                            # ігноруємо, лишаємо cand
    elif p == 'bass_chord' and num == 4:
        cand = (bar_ql / 4, ['B', 'A', 'B', 'A'])

    beat_ql, pat = cand
    assert abs(beat_ql * len(pat) - bar_ql) < 1e-6, \
        f'патерн {pat} не вкладається в такт {ts.ratioString}'
    return beat_ql, pat


def build_left_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    Ліва рука, побудована ПО ТАКТАХ (а не по спанах акордів, як у v1).
    Саме це гарантує, що ліва рука має ту саму довжину, що й права.
    """
    bar_ql = ctx.ts.barDuration.quarterLength
    beat_ql, pattern = _lh_pattern_for(ctx.ts, cfg)
    out: List[note.GeneralNote] = []

    n_bars = max(1, int(round(ctx.total_ql / bar_ql)))
    for bar in range(n_bars):
        bar_off = bar * bar_ql
        for i, role in enumerate(pattern):
            off = bar_off + i * beat_ql
            if off >= ctx.total_ql - 1e-6:
                break
            cs = ctx.chord_at(off)
            if cs is None:
                r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = off
                out.append(r)
                continue

            if role in ('B', 'F'):
                base = cs.root() if role == 'B' else (cs.fifth or cs.root())
                p = pitch.Pitch(base.name)
                p.octave = cfg.lh_bass_octave
                el = note.Note(p)
            else:
                el = chord.Chord(_stradella_voicing(cs, cfg.lh_chord_octave))
            el.duration.quarterLength = beat_ql
            el.offset = off
            out.append(el)
    return out


# =================================================================
#  ШАР 3. СКЛАДАЛЬНИК ПАРТИТУРИ
# =================================================================


def _assemble_part(elements, ctx: ArrangeContext, cl: clef.Clef,
                   part_id: str, name: str) -> stream.Part:
    p = stream.Part(id=part_id)
    p.partName = name
    p.insert(0, cl)
    p.insert(0, key.KeySignature(ctx.key.sharps))
    p.insert(0, meter.TimeSignature(ctx.ts.ratioString))
    for el in elements:
        p.insert(el.offset, el)
    p.makeNotation(inPlace=True)     # <- такти, тактові риски, в'язки, групування
    return p


def arrange(source, cfg: Optional[ArrangeConfig] = None) -> stream.Score:
    cfg = cfg or ArrangeConfig()
    ctx = parse_input(source)
    for w in ctx.warnings:
        print('  [!] ' + w)

    rh_elems = build_right_hand(ctx, cfg)
    lh_elems = build_left_hand(ctx, cfg)

    rh = _assemble_part(rh_elems, ctx, clef.TrebleClef(), 'right-hand', 'Права рука')
    lh = _assemble_part(lh_elems, ctx, clef.BassClef(), 'left-hand', 'Ліва рука')

    sc = stream.Score()
    sc.insert(0, tempo.MetronomeMark(number=96))
    sc.insert(0, rh)
    sc.insert(0, lh)
    sc.insert(0, layout.StaffGroup([rh, lh], name='Баян', symbol='brace',
                                   barTogether=True))
    return sc


def to_musicxml_string(sc: stream.Score) -> str:
    from music21.musicxml.m21ToXml import GeneralObjectExporter
    return GeneralObjectExporter(sc).parse().decode('utf-8')


# --- готові пресети (для порівняння у розділі 4 диплому) ---

PRESETS = {
    'eighths_ct':   ArrangeConfig(subdivision=2, second_strategy='chord_tone',
                                  name='Вісімки / акордовий тон'),
    'eighths_nb':   ArrangeConfig(subdivision=2, second_strategy='neighbor_away',
                                  name='Вісімки / допоміжний тон'),
    'sixteenths_nb': ArrangeConfig(subdivision=4, tight_figure='neighbor',
                                   name='Шістнадцяті / оспівування'),
    'sixteenths_arp': ArrangeConfig(subdivision=4, tight_figure='arpeggio',
                                    name='Шістнадцяті / арпеджіо'),
    'mixed':        ArrangeConfig(subdivision=2, cadence_subdivision=4,
                                  name='Мікс (каденції — 16-ті)'),
    'waltz':        ArrangeConfig(subdivision=2, lh_pattern='waltz', name='Вальс'),
}


# =================================================================
#  CLI
# =================================================================

if __name__ == '__main__':
    import argparse, sys
    ap = argparse.ArgumentParser(description='Генератор баянного аранжування')
    ap.add_argument('input', help='вхідний MusicXML (мелодія + акорди)')
    ap.add_argument('-o', '--output', default='arranged.musicxml')
    ap.add_argument('-p', '--preset', default='mixed', choices=list(PRESETS))
    ap.add_argument('--all', action='store_true',
                    help='згенерувати всі пресети для порівняння')
    a = ap.parse_args()

    if a.all:
        for nm, cfg in PRESETS.items():
            fp = a.output.replace('.musicxml', f'__{nm}.musicxml')
            arrange(a.input, cfg).write('musicxml', fp=fp)
            print(f'{cfg.name:32s} -> {fp}')
    else:
        arrange(a.input, PRESETS[a.preset]).write('musicxml', fp=a.output)
        print(f'{PRESETS[a.preset].name} -> {a.output}')
