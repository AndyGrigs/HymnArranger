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
import copy
import random
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from music21 import (
    stream, note, chord, harmony, key, meter, clef,
    pitch, converter, layout, tempo, expressions, bar,
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
    pickup_ql: float = 0.0               # довжина затакту; 0 = затакту немає

    def in_pickup(self, offset: float) -> bool:
        return offset < self.pickup_ql - 1e-6

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

    # --- ЗАТАКТ: неповний перший такт ---
    pickup_ql = 0.0
    if measures:
        m0 = measures[0]
        filled = sum(e.duration.quarterLength for e in m0.notesAndRests
                     if not isinstance(e, harmony.ChordSymbol))
        if m0.paddingLeft and m0.paddingLeft > 0:
            pickup_ql = bar_ql - m0.paddingLeft
        elif filled > 0 and filled < bar_ql - 1e-6:
            pickup_ql = filled
        elif m0.number == 0:
            pickup_ql = filled

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
    # округлюємо до цілих тактів, відлічуючи ПІСЛЯ затакту
    body = total - pickup_ql
    if body % bar_ql > 1e-6:
        body = (int(body // bar_ql) + 1) * bar_ql
    total = pickup_ql + body

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

    if pickup_ql > 1e-6:
        warns.append(f'Виявлено затакт ({pickup_ql} чв.) — залишаю без змін.')

    return ArrangeContext(events=events, chords=uniq, key=k, ts=ts,
                          total_ql=total, warnings=warns, chord_source=source,
                          pickup_ql=pickup_ql)


# =================================================================
#  ШАР 2a. ДІАТОНІЧНІ ПРИМІТИВИ
# =================================================================


def _step(p: pitch.Pitch, k: key.Key, direction: int, cs=None) -> pitch.Pitch:
    """
    Сусідній діатонічний ступінь тональності вгору (+1) чи вниз (-1).

    Якщо передано активний акорд, ГАРМОНІЯ МАЄ ПРІОРИТЕТ над ключовими
    знаками: коли акорд містить альтерований варіант того самого ступеня,
    беремо його. Без цього в мінорі фігурація видавала соль-бекар під
    домінантою з соль-дієзом — перехресне відношення в сусідніх нотах.
    """
    # УВАГА: k.next() — це успадкований Music21Object.next() (навігація по
    # потоку), він кидає виняток. Діатонічний крок дає саме nextPitch()
    # з ЧИСЛОВИМ напрямком.
    try:
        res = k.nextPitch(p, 1 if direction > 0 else -1)
    except Exception:
        res = None
    if res is None:
        res = p.transpose(2 * direction)
    out = pitch.Pitch(res.nameWithOctave)

    if cs is not None:
        try:
            tones = cs.pitches
        except Exception:
            tones = []
        for t in tones:
            if t.step == out.step and t.pitchClass != out.pitchClass \
                    and abs((t.alter or 0) - (out.alter or 0)) <= 1:
                fixed = pitch.Pitch(t.name)
                fixed.octave = out.octave
                if abs(fixed.midi - out.midi) <= 1:
                    return fixed
    return out


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
                   k: key.Key, cs=None) -> pitch.Pitch:
    """Ввідний тон до target з боку from_side. Ніколи не дорівнює target."""
    if target.midi == from_side.midi:
        return _step(target, k, -1, cs)
    return _step(target, k, -1 if from_side.midi < target.midi else 1, cs)


# =================================================================
#  ШАР 2b. КОНФІГ І РУШІЙ ФІГУРАЦІЇ
# =================================================================


SECOND_STRATEGIES = ('chord_tone', 'neighbor_away')
LH_PATTERNS = ('bass_chord', 'bass_alt_fifth', 'waltz', 'auto')


@dataclass
class ArrangeConfig:
    """Один об'єкт = один стиль аранжування. Новий стиль != новий цикл коду."""
    unit_ql: float = 0.5                 # ЦІЛЬОВА тривалість: 0.5=вісімка, 0.25=16-та
    cadence_unit_ql: Optional[float] = None     # дрібніше на останній ноті такту
    max_parts: int = 8                   # стеля дроблення однієї ноти
    preserve_final: bool = True          # останню ноту твору не чіпати
    min_ql_to_split: float = 0.0         # абсолютна підлога (0 = без обмеження);
                                         # реальний критерій — чи вміщаються
                                         # хоча б дві частки unit_ql
    second_strategy: str = 'chord_tone'  # як розв'язувати "впирання" в секунду
    tight_figure: str = 'neighbor'       # 'neighbor' (оспівування) | 'arpeggio'
    lh_pattern: str = 'auto'
    alt_bass_on_change: bool = False     # False = на зміні акорду бас бере приму
    lh_voice_leading: bool = True        # обирати обернення, найближче до попереднього
    lh_chord_lo_midi: int = 48           # C3 — межі, у яких може лежати нижня нота акорду
    lh_chord_hi_midi: int = 64           # E4
    lh_bass_octave: int = 2
    lh_chord_octave: int = 3
    rh_min_midi: int = 53                # F3 — низ правої клавіатури баяна
    rh_max_midi: int = 96                # C7
    # --- режим аранжування ---
    mode: str = 'figuration'
    #   'melody_plain'        — мелодія без змін + стандартна ліва (приклад 3а)
    #   'two_voice_arp'       — 2 голоси: мелодія + арпеджіо 16-ми (приклад 4а)
    #   'figuration'          — обігравання мелодії (базовий)
    #   'chord_melody'        — акордова мелодія (приклад 1)
    #   'bass_melody_single'  — мелодія в басі, права відбиває поодинокими (2б)
    #   'bass_melody_chords'  — мелодія в басі, права відбиває тризвуками (2в)
    #   'bass_melody_dyad'    — мелодія в басі, R R нота двозвук (2б_new)
    #   'bass_melody_thirds'  — мелодія в басі, права в терцію/сексту до неї (2г)
    pulse_unit_ql: float = 0.25       # тривалість удару в режимах 2а/2б/2в
                                      # (кількість часток = ql ноти / pulse_unit_ql,
                                      #  але не більше max_parts)
    pulse_floor_midi: int = 64        # E4 — підлога регістру правої руки
    bass_melody_octaves: Optional[int] = None   # None = підібрати автоматично
    bass_target_midi: int = 48        # C3 — куди має лягти найнижча нота мелодії
    octave_shift: int = 0             # зсув правої руки в октавах (для фіналу)
    arp_unit_ql: float = 0.25         # тривалість ноти арпеджіо в режимі two_voice_arp
    arp_shape: Tuple[int, ...] = (0, 1, 2, 1)   # індекси тонів акорду у фігурі
    thirds_floor_midi: int = 64       # E4 — низ регістру для режиму 2г
    thirds_note_ql: float = 2.0       # тривалість ноти супроводу в режимі 2г
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
            fill = _step(cur, k, -1, cs)
        elif steps <= 1:                                 # СЕКУНДА — спірний випадок
            if cfg.second_strategy == 'chord_tone':
                fill = _nearest_chord_tone(cs, cur, -1, k)
            else:                                        # neighbor_away
                fill = _step(cur, k, -1 if diff > 0 else 1, cs)
        elif steps == 2:                                 # терція -> прохідний тон
            fill = _step(cur, k, 1 if diff > 0 else -1, cs)
        else:                                            # стрибок -> тон акорду всередині
            fill = _chord_tone_between(cs, cur, target, k)
        if fill.midi == target.midi:                     # страхівка від дублювання
            fill = _step(cur, k, -1 if diff > 0 else 1, cs)
        return [cur, _clamp(fill, cfg)]

    # --- n_parts >= 3: [мелодія, заповнення..., ввідний тон] ---
    approach = _approach_tone(target, cur, k, cs)
    n_fill = n_parts - 2
    fill: List[pitch.Pitch] = []

    fill_steps = abs(_steps_between(cur, approach, k))
    if fill_steps >= n_fill + 1:
        # достатньо місця для гамоподібного руху
        direction = 1 if approach.midi > cur.midi else -1
        p = cur
        for _ in range(n_fill):
            p = _step(p, k, direction, cs)
            fill.append(p)
    elif cfg.tight_figure == 'neighbor':
        # ОСПІВУВАННЯ: cur -> допоміжний з протилежного від цілі боку -> cur ...
        # Дає плавний хоральний рух замість октавних стрибків.
        away = _step(cur, k, -1 if target.midi > cur.midi else 1, cs)
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
    figure = _dedupe(figure, target, cs, k)
    figure[0] = cur                                       # інваріант сильної долі
    return [_clamp(p, cfg) for p in figure]


def _dedupe(figure: List[pitch.Pitch], target: pitch.Pitch,
            cs, k: key.Key) -> List[pitch.Pitch]:
    """
    Два інваріанти фігури:
      - жодна нота не дорівнює наступній ноті мелодії (немає передчасного показу);
      - жодні дві СУСІДНІ ноти не однакові (немає застряглого повтору).
    Другий інваріант і давав 'G4 F4 G4 G4' наприкінці кожної каденції.
    """
    out = [figure[0]]
    for i in range(1, len(figure)):
        p = figure[i]
        for attempt in range(4):
            bad = (p.midi == out[-1].midi) or (p.midi == target.midi)
            if not bad:
                break
            # пробуємо по черзі: крок вниз, крок вгору, тон акорду поруч
            if attempt == 0:
                p = _step(out[-1], k, -1, cs)
            elif attempt == 1:
                p = _step(out[-1], k, 1, cs)
            else:
                p = _nearest_chord_tone(cs, out[-1], -1 if attempt == 2 else 1, k)
        out.append(p)
    return out


def build_right_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """Права рука: мелодія з фігурацією. Повертає ноти з абсолютними offset'ами."""
    bar_ql = ctx.ts.barDuration.quarterLength
    # останні звучні ноти кожного такту — для каденційного дроблення
    last_in_measure = {}
    for ev in ctx.events:
        if not ev.is_rest:
            last_in_measure[ev.measure] = ev.offset

    last_sounding_idx = max((i for i, e in enumerate(ctx.events) if not e.is_rest),
                            default=-1)
    out: List[note.GeneralNote] = []
    for i, ev in enumerate(ctx.events):
        if ev.is_rest:
            r = note.Rest()
            r.duration.quarterLength = ev.ql
            r.offset = ev.offset
            out.append(r)
            continue

        n_parts = 1
        is_final = (i == last_sounding_idx)
        if (ev.ql >= cfg.min_ql_to_split
                and not ctx.in_pickup(ev.offset)          # затакт не чіпаємо
                and not (cfg.preserve_final and is_final)):
            unit = cfg.unit_ql
            if (cfg.cadence_unit_ql
                    and last_in_measure.get(ev.measure) == ev.offset):
                unit = cfg.cadence_unit_ql
            # ключове: кількість часток виводиться з ТРИВАЛОСТІ ноти,
            # тому половинна дає 4 вісімки, а ціла — 8, а не завжди дві частини
            # нота дробиться лише якщо в ній вміщається >= 2 частки:
            # вісімку не можна обіграти вісімками, але можна шістнадцятими
            n_parts = max(1, min(cfg.max_parts, int(ev.ql / unit + 1e-6)))

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




# ---------------- НОВІ РЕЖИМИ ФАКТУРИ ----------------

def _chord_tones_from(cs, floor: pitch.Pitch, count: int,
                      k: key.Key) -> List[pitch.Pitch]:
    """count тонів акорду підряд угору, починаючи з першого >= floor."""
    if cs is None:
        return [floor] * count
    names = [p.name for p in cs.pitches]
    out, octv = [], floor.octave - 1
    while len(out) < count + 8 and octv < floor.octave + 4:
        for nm in names:
            q = pitch.Pitch(nm); q.octave = octv
            out.append(q)
        octv += 1
    out = sorted(set(out), key=lambda x: x.midi)
    above = [p for p in out if p.midi >= floor.midi]
    while len(above) < count:
        above.append(above[-1].transpose(12) if above else floor)
    return above[:count]


def build_melody_plain(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 3а — чисте проведення теми.
    Мелодія не змінюється взагалі; сенс у тому, щоб слухач почув тему
    цілком, перш ніж вона піде у варіації.
    """
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            el = note.Rest()
        else:
            p = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
            el = note.Note(_clamp(pitch.Pitch(p.nameWithOctave), cfg))
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        out.append(el)
    return out


def build_chord_melody(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 1 — акордова мелодія.
    Мелодія лишається верхнім голосом; знизу вона дублюється на октаву,
    а два вільні місця між ними заповнюються рештою тонів акорду.
    """
    # акордова мелодія дублює тему НА ОКТАВУ ВНИЗ, тож для гімну, записаного
    # низько, нижній голос вилітає під праву клавіатуру. Підбираємо зсув так,
    # щоб найнижчий тон акорду лишався в межах інструмента.
    shift = cfg.octave_shift
    lows = [e.pitch.midi for e in ctx.events if not e.is_rest]
    if lows:
        while min(lows) + 12 * shift - 12 < cfg.rh_min_midi:
            shift += 1

    out = []
    for ev in ctx.events:
        if ev.is_rest:
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
            out.append(r); continue
        if ctx.in_pickup(ev.offset):
            n = note.Note(ev.pitch); n.duration.quarterLength = ev.ql
            n.offset = ev.offset; out.append(n); continue

        top = ev.pitch.transpose(12 * shift) if shift else ev.pitch
        cs = ctx.chord_at(ev.offset)
        bottom = top.transpose(-12)
        inner = [p for p in _chord_tones_from(cs, bottom, 8, ctx.key)
                 if bottom.midi < p.midi < top.midi][:2]
        pitches = [bottom] + inner + [top]
        c = chord.Chord(sorted(set(p.nameWithOctave for p in pitches),
                              key=lambda s: pitch.Pitch(s).midi))
        c.duration.quarterLength = ev.ql
        c.offset = ev.offset
        out.append(c)
    return out


def _bass_shift(ctx: ArrangeContext, cfg: ArrangeConfig) -> int:
    """
    Скільки октав опустити мелодію в бас. Фіксоване число ламається,
    щойно вхідний гімн записано в іншій октаві: те саме -2 давало C3 на
    одному матеріалі і C2 на іншому. Тому прив'язуємось до РЕГІСТРУ:
    найнижча нота мелодії має лягти приблизно на bass_target_midi.
    """
    if cfg.bass_melody_octaves is not None:
        return cfg.bass_melody_octaves
    lows = [e.pitch.midi for e in ctx.events if not e.is_rest]
    if not lows:
        return -1
    return int(round((cfg.bass_target_midi - min(lows)) / 12.0))


def build_pulse_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАДИ 2б / 2в — права рука відбиває ритм.
    На кожну ноту мелодії: пауза на сильній частці + (pulse_parts-1) ударів.
    'single' — поодинокі тони акорду за схемою верх-низ-верх;
    'chords' — тризвук у тісному розташуванні, що йде за мелодією.
    """
    triads = (cfg.mode == 'bass_melody_chords')
    dyad = (cfg.mode == 'bass_melody_dyad')
    shift = _bass_shift(ctx, cfg)
    out = []
    for ev in ctx.events:
        if ev.is_rest or ctx.in_pickup(ev.offset):
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
            out.append(r); continue

        cs = ctx.chord_at(ev.offset)
        # кількість ударів виводиться з ТРИВАЛОСТІ ноти, а не фіксована:
        # саме це відрізняє приклад 2а (вісімки) від 2в (шістнадцяті)
        n_parts = int(round(ev.ql / cfg.pulse_unit_ql))
        n_parts = max(2, min(cfg.max_parts, n_parts))
        sub = ev.ql / n_parts

        # У режимі "пауза-нота-двозвук" паузи на початку долі зливаються
        # в одну (дві шістнадцяті -> вісімкова), інакше нотний текст рябіє.
        rest_ql = sub * (n_parts - 2) if dyad else sub
        r = note.Rest(); r.duration.quarterLength = rest_ql; r.offset = ev.offset
        out.append(r)

        # мелодія вже звучить у басу; права рука сидить над нею,
        # але не нижче підлоги регістру
        bass = ev.pitch.transpose(12 * shift)
        floor = pitch.Pitch(midi=max(cfg.pulse_floor_midi, bass.midi + 12))

        if dyad:
            # ПРИКЛАД 2б_new: [пауза, пауза, нижня нота, двозвук]
            low = _chord_tones_from(cs, floor, 1, ctx.key)[0]
            highs = _chord_tones_from(cs, pitch.Pitch(midi=low.midi + 1), 2, ctx.key)
            # вступна пауза вже додана вище, тож тут лишається n_parts-1 позицій
            base = ev.offset + rest_ql
            n1 = note.Note(low)
            n1.duration.quarterLength = sub; n1.offset = base
            n2 = chord.Chord([p.nameWithOctave for p in highs])
            n2.duration.quarterLength = sub; n2.offset = base + sub
            out.extend([n1, n2])
        elif triads:
            voicing = _chord_tones_from(cs, floor, 3, ctx.key)
            for j in range(1, n_parts):
                c = chord.Chord([p.nameWithOctave for p in voicing])
                c.duration.quarterLength = sub
                c.offset = ev.offset + j * sub
                out.append(c)
        else:
            low = _chord_tones_from(cs, floor, 1, ctx.key)[0]
            # верхні тони — наступні тони акорду СТРОГО вище нижнього
            highs = _chord_tones_from(cs, pitch.Pitch(midi=low.midi + 1), 4, ctx.key)
            seq = []
            hi = 0
            for j in range(1, n_parts):
                if j % 2 == 1:
                    seq.append(highs[hi % len(highs)]); hi += 1
                else:
                    seq.append(low)
            for j, p in enumerate(seq, start=1):
                nn = note.Note(p)
                nn.duration.quarterLength = sub
                nn.offset = ev.offset + j * sub
                out.append(nn)
    return out


def build_bass_melody(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """Ліва рука для режимів 2б/2в: мелодія, перенесена в басовий регістр."""
    shift = 12 * _bass_shift(ctx, cfg)
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
        else:
            r = note.Note(ev.pitch.transpose(shift))
            r.duration.quarterLength = ev.ql
        r.offset = ev.offset
        out.append(r)
    return out



def build_two_voice_arp(ctx: ArrangeContext, cfg: ArrangeConfig):
    """
    ПРИКЛАД 4а — два самостійні голоси на одному нотоносці.
      голос 2: мелодія без змін (довгі тривалості);
      голос 1: безперервне арпеджіо шістнадцятими.

    Фігура будується від ноти мелодії вгору по тонах акорду і назад:
    C4 -> E4 -> G4 -> E4. На відміну від інших режимів дроблення тут
    прив'язане до ДОЛІ, а не до тривалості ноти: витримана половинна
    все одно отримує рівний рух шістнадцятими.
    """
    beat_ql = ctx.ts.beatDuration.quarterLength
    n_arp = max(2, int(round(beat_ql / cfg.arp_unit_ql)))
    shape = cfg.arp_shape

    # голос 2 — мелодія як є
    voice_mel = []
    for ev in ctx.events:
        el = note.Rest() if ev.is_rest else note.Note(ev.pitch)
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        voice_mel.append(el)

    # мелодія, що звучить на кожній долі
    def sounding(off):
        cur = None
        for ev in ctx.events:
            if ev.offset <= off + 1e-6 < ev.offset + ev.ql:
                cur = ev
        return cur

    voice_arp = []
    off = 0.0
    while off < ctx.total_ql - 1e-6:
        ev = sounding(off)
        if ev is None or ev.is_rest or ctx.in_pickup(off):
            r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = off
            voice_arp.append(r); off += beat_ql; continue

        cs = ctx.chord_at(off)
        start = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
        tones = _chord_tones_from(cs, start, max(shape) + 3, ctx.key)
        # Фігура ЗАВЖДИ стартує з ноти мелодії — саме це робить фактуру
        # двоголосою на слух. Якщо нота мелодії не входить в акорд
        # (наприклад до під G7), вона все одно лишається першою,
        # а далі йдуть тони акорду над нею.
        above = [t for t in tones if t.midi > start.midi]
        tones = [pitch.Pitch(start.nameWithOctave)] + above
        while len(tones) < max(shape) + 1:
            tones.append(tones[-1].transpose(12))

        sub = beat_ql / n_arp
        for j in range(n_arp):
            idx = shape[j % len(shape)]
            p = tones[min(idx, len(tones) - 1)]
            nn = note.Note(_clamp(pitch.Pitch(p.nameWithOctave), cfg))
            nn.duration.quarterLength = sub
            nn.offset = off + j * sub
            voice_arp.append(nn)
        off += beat_ql

    return (voice_arp, voice_mel)



def build_thirds_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 2г — мелодію веде бас, права рука вступає після паузи
    і тримає ВИТРИМАНІ ноти, що утворюють з басом терцію або сексту.

    Інші інтервали (октава, квінта, секунда) відкидаються свідомо:
    саме терції й сексти дають той повний, "хоровий" призвук, заради
    якого ця фактура й існує. Серед допустимих перевага надається
    тонам активного акорду і найменшому руху від попередньої ноти.
    """
    beat_ql = ctx.ts.beatDuration.quarterLength
    shift = _bass_shift(ctx, cfg)
    CONSONANT = (3, 4, 8, 9)          # м3, в3, м6, в6

    segs = [(e.offset, e.offset + e.ql, e.pitch.transpose(12 * shift))
            for e in ctx.events if not e.is_rest]

    def under(off, dur):
        return [g for g in segs if off < g[1] - 1e-6 and g[0] < off + dur - 1e-6]

    def candidates(bass_list, cs):
        """Висоти, що дають терцію/сексту до КОЖНОГО баса у вікні."""
        chord_pcs = {p.pitchClass for p in cs.pitches} if cs is not None else set()
        out = []
        for semis in CONSONANT:
            for octv in (0, 12, 24):
                p = bass_list[0][2].transpose(semis + octv)
                if p.midi < cfg.thirds_floor_midi or p.midi > cfg.rh_max_midi:
                    continue
                if all((p.midi - g[2].midi) % 12 in CONSONANT for g in bass_list):
                    out.append((0 if (not chord_pcs or p.pitchClass in chord_pcs) else 1, p))
        return out

    out: List[note.GeneralNote] = []
    r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = 0.0
    out.append(r)                                    # обов'язковий вступ з паузи

    prev = None
    off = beat_ql
    first = True
    while off < ctx.total_ql - 1e-6:
        dur = min(beat_ql if first else cfg.thirds_note_ql, ctx.total_ql - off)

        # Якщо під витриманою нотою бас змінюється так, що спільної
        # терції/сексти не існує, КОРОТШАЄМО ноту до зміни баса.
        # Інакше правило "тільки терція або секста" було б порушене.
        pool = []
        while dur > 1e-6:
            bl = under(off, dur)
            if not bl:
                break
            pool = candidates(bl, ctx.chord_at(off))
            if pool:
                break
            nxt = min(g[1] for g in bl if g[1] > off + 1e-6)
            dur = nxt - off

        if not pool:
            el = note.Rest()
        else:
            rank = min(r0 for r0, _ in pool)
            best = [p for r0, p in pool if r0 == rank]
            if prev is None:
                target = cfg.thirds_floor_midi + 2
                p = min(best, key=lambda x: abs(x.midi - target))
            else:
                p = min(best, key=lambda x: (abs(x.midi - prev.midi), x.midi))
            prev = p
            el = note.Note(p)
        el.duration.quarterLength = dur
        el.offset = off
        out.append(el)
        off += dur
        first = False
    return out


# ---------------- ліва рука: Stradella ----------------

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
                base = cs.root() if role == 'B' else (cs.fifth or cs.root())
                p = pitch.Pitch(base.name)
                p.octave = cfg.lh_bass_octave
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
    # затакт має стояти в КІНЦІ неповного такту 0, тому весь матеріал
    # зсуваємо вправо на "недостачу" першого такту
    bar_ql = ctx.ts.barDuration.quarterLength
    shift = (bar_ql - ctx.pickup_ql) if ctx.pickup_ql > 1e-6 else 0.0
    for el in elements:
        p.insert(el.offset + shift, el)
    if shift > 0:
        pad = note.Rest(); pad.duration.quarterLength = shift
        p.insert(0.0, pad)
    p.makeNotation(inPlace=True)     # <- такти, тактові риски, в'язки, групування
    if shift > 0:
        ms = list(p.getElementsByClass(stream.Measure))
        if ms:
            for el in list(ms[0].notesAndRests):
                if el.isRest and el.offset < 1e-6:
                    ms[0].remove(el)          # прибираємо технічну паузу-заповнювач
            ms[0].paddingLeft = shift
            for i, m in enumerate(ms):
                m.number = i                  # затакт = такт 0
    return p


def build_hands(ctx: ArrangeContext, cfg: ArrangeConfig):
    """Диспетчер режимів. Новий режим = нова гілка, а не новий скрипт."""
    if cfg.mode == 'two_voice_arp':
        return build_two_voice_arp(ctx, cfg), build_left_hand(ctx, cfg)
    if cfg.mode == 'melody_plain':
        return build_melody_plain(ctx, cfg), build_left_hand(ctx, cfg)
    if cfg.mode == 'chord_melody':
        return build_chord_melody(ctx, cfg), build_left_hand(ctx, cfg)
    if cfg.mode == 'bass_melody_thirds':
        return build_thirds_hand(ctx, cfg), build_bass_melody(ctx, cfg)
    if cfg.mode in ('bass_melody_single', 'bass_melody_chords', 'bass_melody_dyad'):
        return build_pulse_hand(ctx, cfg), build_bass_melody(ctx, cfg)
    return build_right_hand(ctx, cfg), build_left_hand(ctx, cfg)


def _assemble_two_voice(voices, ctx, cl, part_id, name) -> stream.Part:
    """Збирає ОДИН нотоносець із кількох незалежних голосів.
    music21 виводить їх у MusicXML як <voice>1</voice> / <voice>2</voice>."""
    built = [_assemble_part(v, ctx, cl, f'{part_id}-v{i}', name)
             for i, v in enumerate(voices)]

    p = stream.Part(id=part_id)
    p.partName = name
    mss = [list(b.getElementsByClass(stream.Measure)) for b in built]
    n = max(len(ms) for ms in mss)
    for i in range(n):
        m = stream.Measure(number=i + 1)
        for vi, ms in enumerate(mss):
            if i >= len(ms):
                continue
            src = ms[i]
            if i == 0 and vi == 0:
                for cls in (clef.Clef, key.KeySignature, meter.TimeSignature):
                    el = src.getElementsByClass(cls).first()
                    if el is not None:
                        m.insert(0, copy.deepcopy(el))
            if src.paddingLeft:
                m.paddingLeft = src.paddingLeft
            v = stream.Voice(id=str(vi + 1))
            for el in src.notesAndRests:
                v.insert(el.offset, copy.deepcopy(el))
            m.insert(0, v)
        p.append(m)
    return p


def arrange(source, cfg: Optional[ArrangeConfig] = None,
            quiet: bool = False) -> stream.Score:
    cfg = cfg or ArrangeConfig()
    ctx = parse_input(source)
    if not quiet:
        for w in ctx.warnings:
            print('  [!] ' + w)

    rh_elems, lh_elems = build_hands(ctx, cfg)

    if isinstance(rh_elems, tuple):
        rh = _assemble_two_voice(rh_elems, ctx, clef.TrebleClef(),
                                 'right-hand', 'Права рука')
    else:
        rh = _assemble_part(rh_elems, ctx, clef.TrebleClef(), 'right-hand', 'Права рука')
    lh = _assemble_part(lh_elems, ctx, clef.BassClef(), 'left-hand', 'Ліва рука')

    sc = stream.Score()
    sc.insert(0, tempo.MetronomeMark(number=96))
    sc.insert(0, rh)
    sc.insert(0, lh)
    sc.insert(0, layout.StaffGroup([rh, lh], name='Баян', symbol='brace',
                                   barTogether=True))
    return sc




def arrange_multi(source, presets: Optional[List[str]] = None,
                  cfgs: Optional[List[ArrangeConfig]] = None) -> stream.Score:
    """
    Склеює кілька варіантів аранжування в ОДНУ партитуру, послідовно.
    Кожен варіант отримує репетиційну позначку зі своєю назвою і
    відокремлюється подвійною тактовою рискою — зручно і для порівняння
    на слух, і як ілюстрація до розділу 4 дипломної роботи.
    """
    if cfgs is None:
        names = presets or list(PRESETS)
        cfgs = [PRESETS[n] for n in names]

    ctx = parse_input(source)
    for w in ctx.warnings:
        print('  [!] ' + w)

    rh_all = stream.Part(id='right-hand'); rh_all.partName = 'Права рука'
    lh_all = stream.Part(id='left-hand');  lh_all.partName = 'Ліва рука'
    rh_all.insert(0, clef.TrebleClef())
    lh_all.insert(0, clef.BassClef())
    for part in (rh_all, lh_all):
        part.insert(0, key.KeySignature(ctx.key.sharps))
        part.insert(0, meter.TimeSignature(ctx.ts.ratioString))

    cursor = 0.0
    for idx, cfg in enumerate(cfgs):
        one = arrange(source, cfg, quiet=True)
        for src, dst in ((one.parts[0], rh_all), (one.parts[1], lh_all)):
            ms = list(src.getElementsByClass(stream.Measure))
            for m in ms:
                mm = copy.deepcopy(m)
                mm.removeByClass([clef.Clef, key.KeySignature, meter.TimeSignature])
                mm.number = 0            # перенумеруємо в кінці
                dst.insert(cursor + m.offset, mm)
            last = dst.getElementsByClass(stream.Measure)[-1]
            last.rightBarline = bar.Barline('final' if idx == len(cfgs) - 1
                                            else 'double')
        mark = expressions.RehearsalMark(cfg.name)
        first_new = [m for m in rh_all.getElementsByClass(stream.Measure)
                     if abs(m.offset - cursor) < 1e-6]
        if first_new:
            first_new[0].insert(0, mark)
        cursor += one.parts[0].duration.quarterLength

    for part in (rh_all, lh_all):
        for i, m in enumerate(part.getElementsByClass(stream.Measure), start=1):
            m.number = i

    sc = stream.Score()
    sc.insert(0, tempo.MetronomeMark(number=96))
    sc.insert(0, rh_all)
    sc.insert(0, lh_all)
    sc.insert(0, layout.StaffGroup([rh_all, lh_all], name='Баян',
                                   symbol='brace', barTogether=True))
    return sc




# =================================================================
#  СЦЕНАРІЙ: сюїта варіацій
# =================================================================

# Один зі списку обирається випадково. Так фінальний твір щоразу
# трохи інший, але завжди в межах перевірених режимів.
BASS_LED = ['bass_chords_8', 'bass_single', 'bass_chords', 'bass_thirds']

SUITE_PLAN = [
    'theme',              # 1. тема цілком — слухач має впізнати мелодію
    'eighths_nb',         # 2. перше обігравання: вісімки, допоміжний тон
    'sixteenths_nb',      # 3. дрібніше: шістнадцяті, оспівування
    'eighths_ct',         # 4. назад до вісімок, але через тони акорду
    'mixed',              # 5. вісімки з каденціями шістнадцятими — місток
    'sixteenths_arp',     # 6. шістнадцяті арпеджіо — віртуозна варіація
    BASS_LED,             # 7. зміна фактури: мелодію веде ліва рука
    'two_voice_arp',      # 8. два голоси: тема повертається під арпеджіо
    'chord_melody_8va',   # 9. фінал акордами, октавою вище
]


def resolve_suite(plan=None, seed: Optional[int] = None) -> List[str]:
    """
    Розгортає план сюїти у конкретний список пресетів.
    seed фіксує випадковий вибір — потрібно, щоб результат
    у дипломній роботі можна було відтворити.
    """
    rng = random.Random(seed)
    out = []
    for step in (plan or SUITE_PLAN):
        out.append(rng.choice(step) if isinstance(step, (list, tuple)) else step)
    return out


def arrange_suite(source, plan=None, seed: Optional[int] = None) -> stream.Score:
    """Повна п'єса: тема + варіації, склеєні в одну партитуру."""
    names = resolve_suite(plan, seed)
    print('  Сюїта: ' + ' -> '.join(PRESETS[n].name for n in names))
    return arrange_multi(source, presets=names)


def to_musicxml_string(sc: stream.Score) -> str:
    from music21.musicxml.m21ToXml import GeneralObjectExporter
    return GeneralObjectExporter(sc).parse().decode('utf-8')


# --- готові пресети (для порівняння у розділі 4 диплому) ---

PRESETS = {
    'eighths_ct':    ArrangeConfig(unit_ql=0.5, second_strategy='chord_tone',
                                   name='Вісімки / акордовий тон'),
    'eighths_nb':    ArrangeConfig(unit_ql=0.5, second_strategy='neighbor_away',
                                   name='Вісімки / допоміжний тон'),
    'sixteenths_nb': ArrangeConfig(unit_ql=0.25, tight_figure='neighbor', max_parts=16,
                                   name='Шістнадцяті / оспівування'),
    'sixteenths_arp': ArrangeConfig(unit_ql=0.25, tight_figure='arpeggio', max_parts=16,
                                    name='Шістнадцяті / арпеджіо'),
    'mixed':         ArrangeConfig(unit_ql=0.5, cadence_unit_ql=0.25,
                                   name='Мікс (каденції — 16-ті)'),
    'waltz':         ArrangeConfig(unit_ql=0.5, lh_pattern='waltz', name='Вальс'),
    'theme':         ArrangeConfig(mode='melody_plain',
                                   name='Тема'),
    'two_voice_arp': ArrangeConfig(mode='two_voice_arp',
                                   name='Два голоси: мелодія + арпеджіо 16-ми'),
    'chord_melody':  ArrangeConfig(mode='chord_melody',
                                   name='Акордова мелодія'),
    'chord_melody_8va': ArrangeConfig(mode='chord_melody', octave_shift=1,
                                      rh_max_midi=100,
                                      name='Акордова мелодія (октавою вище)'),
    'bass_chords_8': ArrangeConfig(mode='bass_melody_chords', pulse_floor_midi=64, pulse_unit_ql=0.5, max_parts=4,
                                   name='Мелодія в басі / тризвуки вісімками'),
    'bass_single':   ArrangeConfig(mode='bass_melody_dyad', pulse_floor_midi=67,
                                   pulse_unit_ql=0.25, max_parts=4,
                                   name='Мелодія в басі / пауза-нота-двозвук'),
    'bass_thirds':   ArrangeConfig(mode='bass_melody_thirds',
                                   name='Мелодія в басі / терції-сексти'),
    'bass_chords':   ArrangeConfig(mode='bass_melody_chords', pulse_floor_midi=64, pulse_unit_ql=0.25, max_parts=4,
                                   name='Мелодія в басі / тризвуки шістнадцятими'),
}


# =================================================================
#  CLI
# =================================================================

if __name__ == '__main__':
    import argparse, sys, glob as _glob
    from pathlib import Path

    INPUT_DIR = Path(__file__).parent / 'input'
    OUTPUT_DIR = Path(__file__).parent / 'output'

    ap = argparse.ArgumentParser(description='Генератор баянного аранжування')
    ap.add_argument('input', nargs='?',
                    help='вхідний MusicXML; якщо не вказано — береться перший файл з ./input/')
    ap.add_argument('-o', '--output',
                    help='вихідний файл; за замовчуванням ./output/<ім\'я_файлу>.mxl')
    ap.add_argument('-p', '--preset', default='mixed', choices=list(PRESETS))
    ap.add_argument('--all', action='store_true',
                    help='згенерувати всі пресети окремими файлами')
    ap.add_argument('--merge', action='store_true',
                    help='склеїти УСІ пресети в одну партитуру')
    ap.add_argument('--suite', action='store_true',
                    help='зібрати готову п\'єсу: тема + варіації')
    ap.add_argument('--seed', type=int, default=None,
                    help='зерно випадковості для --suite (для відтворюваності)')
    a = ap.parse_args()

    # --- визначаємо вхідний файл ---
    if a.input:
        in_path = Path(a.input)
    else:
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        candidates = (sorted(INPUT_DIR.glob('*.mxl'))
                      + sorted(INPUT_DIR.glob('*.musicxml'))
                      + sorted(INPUT_DIR.glob('*.xml')))
        if not candidates:
            sys.exit(f'Помилка: не знайдено жодного .mxl/.musicxml/.xml у {INPUT_DIR}')
        in_path = candidates[0]
        print(f'Вхідний файл: {in_path}')

    # --- визначаємо вихідний файл ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if a.output:
        out_path = Path(a.output)
    else:
        out_path = OUTPUT_DIR / (in_path.stem + '.mxl')

    if a.suite:
        arrange_suite(str(in_path), seed=a.seed).write('mxl', fp=str(out_path))
        print(f'Сюїта -> {out_path}')
    elif a.merge:
        arrange_multi(str(in_path)).write('mxl', fp=str(out_path))
        print(f'Склеєна партитура ({len(PRESETS)} розділів) -> {out_path}')
    elif a.all:
        for nm, cfg in PRESETS.items():
            fp = out_path.parent / f'{out_path.stem}__{nm}.mxl'
            arrange(str(in_path), cfg).write('mxl', fp=str(fp))
            print(f'{cfg.name:32s} -> {fp}')
    else:
        arrange(str(in_path), PRESETS[a.preset]).write('mxl', fp=str(out_path))
        print(f'{PRESETS[a.preset].name} -> {out_path}')
