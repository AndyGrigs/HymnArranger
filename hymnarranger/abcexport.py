"""Шар 4 — зворотна конвертація партитури music21 у ABC-нотацію.

music21 читає ABC, але НЕ вміє його писати: у `music21.abcFormat.translate`
є лише `abcToStream*`, зворотної функції немає. Виклик `score.write('abc')`
мовчки віддає роботу текстовому субконвертеру і записує `repr()` об'єкта.
Тому експорт доводиться писати самостійно.

Підтримувана підмножина ABC достатня для баянних аранжувань:
  * заголовки X, T, C, M, L, Q, K
  * два нотоносці як два голоси (`%%score {1 | 2}`) з ключами treble/bass
  * ноти, співзвуччя `[CEG]`, паузи, крапки, тріолі
  * знаки альтерації з урахуванням тональності і меж такту
  * ліги продовження (tie), тактові риски, репризи, репетиційні позначки
  * затакт (неповний перший такт)

Не підтримується (свідомо): динаміка, артикуляція, вкладені тріолі
складніші за 3:2, спанери-ліги (slur), кілька систем на нотоносець.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from music21 import (bar, chord, clef, expressions, harmony, key, meter, note,
                     stream, tempo)


# =================================================================
#  Константи
# =================================================================

#: Базова одиниця тривалості в ABC (L:1/8). Вибрана під редактор на фронті —
#: `AbcEditor` генерує мелодії з тим самим L, тож туди-сюди все узгоджено.
UNIT_LENGTH = Fraction(1, 8)

#: Скільки чвертних тривалостей в одній одиниці L.
_UNIT_QL = UNIT_LENGTH * 4  # 1/8 такту == 0.5 чвертки

#: Порядок дієзів/бемолів у ключових знаках.
_SHARP_ORDER = ['F', 'C', 'G', 'D', 'A', 'E', 'B']
_FLAT_ORDER = ['B', 'E', 'A', 'D', 'G', 'C', 'F']

#: sharps → назва тональності в ABC (мажор).
_MAJOR_BY_SHARPS = {
    -7: 'Cb', -6: 'Gb', -5: 'Db', -4: 'Ab', -3: 'Eb', -2: 'Bb', -1: 'F',
    0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#',
}

_ACCIDENTAL_ABC = {-2: '__', -1: '_', 0: '=', 1: '^', 2: '^^'}

_BARLINE_ABC = {
    'regular': '|',
    'double': '||',
    'final': '|]',
    'heavy': '|]',
    'dashed': ':',
    'dotted': ':',
    'none': '',
}


# =================================================================
#  1. Висота ноти
# =================================================================

def key_accidentals(sharps: int) -> Dict[str, int]:
    """Які ступені альтеровані самим ключем.

    Повертає {'F': 1, 'C': 1} для двох дієзів. Потрібно, щоб не друкувати
    дієз біля кожної фа в ре мажорі — ABC, як і звичайна нотація, розуміє
    ключові знаки.
    """
    if sharps > 0:
        return {step: 1 for step in _SHARP_ORDER[:sharps]}
    if sharps < 0:
        return {step: -1 for step in _FLAT_ORDER[:abs(sharps)]}
    return {}


def pitch_to_abc(pitch, sharps: int, measure_state: Dict[Tuple[str, int], int]) -> str:
    """Одна висота → ABC-фрагмент без тривалості.

    `measure_state` — накопичувач альтерацій у межах поточного такту:
    ключ (ступінь, октава), значення — alter, який зараз діє. Знак
    друкується лише тоді, коли реальна альтерація ноти відрізняється від
    того, що вже діє (з ключа або з попереднього знака в цьому такті).
    Саме так працює і нотний запис, і парсер abcjs.
    """
    step = pitch.step
    octv = pitch.octave if pitch.octave is not None else 4
    alter = int(pitch.alter)

    slot = (step, octv)
    effective = measure_state.get(slot)
    if effective is None:
        effective = key_accidentals(sharps).get(step, 0)

    prefix = ''
    if alter != effective:
        prefix = _ACCIDENTAL_ABC.get(alter, '')
        measure_state[slot] = alter

    # ABC: C == до першої октави (C4), c == C5, C, == C3, c' == C6
    if octv >= 5:
        letter = step.lower() + "'" * (octv - 5)
    else:
        letter = step + ',' * (4 - octv)

    return prefix + letter


# =================================================================
#  2. Тривалість
# =================================================================

def duration_to_abc(quarter_length) -> str:
    """Тривалість у чвертках → множник відносно L.

    При L:1/8 чвертка = 2, вісімка = порожній рядок, шістнадцята = /2,
    чвертка з крапкою = 3, тріольна вісімка = 2/3.
    """
    if quarter_length <= 0:
        return ''
    ratio = Fraction(quarter_length).limit_denominator(64) / _UNIT_QL

    if ratio == 1:
        return ''
    if ratio.denominator == 1:
        return str(ratio.numerator)
    if ratio.numerator == 1:
        return f'/{ratio.denominator}'
    return f'{ratio.numerator}/{ratio.denominator}'


# =================================================================
#  3. Окремі елементи
# =================================================================

def _tie_suffix(el) -> str:
    """Ліга продовження. У ABC вона позначається дефісом ПІСЛЯ ноти."""
    tie = getattr(el, 'tie', None)
    if tie is not None and tie.type in ('start', 'continue'):
        return '-'
    return ''


def chord_symbol_to_abc(cs) -> str:
    """`harmony.ChordSymbol` → текст для лапок ABC ("Am", "G7", "Bb").

    music21 пише бемоль як дефіс ('B-m7'), ABC і abcjs очікують 'Bbm7'.
    Порожню фігуру (N.C.) пропускаємо.
    """
    fig = (cs.figure or '').strip()
    if not fig or fig.upper().startswith('N.C'):
        return ''
    return fig.replace('-', 'b')


def element_to_abc(el, sharps: int, measure_state: Dict[Tuple[str, int], int]) -> str:
    """Нота / співзвуччя / пауза → ABC.

    `harmony.ChordSymbol` — підклас `chord.Chord`, тож він теж потрапляє
    в `notesAndRests`. Якщо його не відсіяти, акордовий підпис "Bb"
    надрукується ще й як реальне співзвуччя [B,,D,F,].
    """
    if isinstance(el, harmony.ChordSymbol):
        return ''

    dur = duration_to_abc(el.duration.quarterLength)

    if isinstance(el, note.Rest):
        return 'z' + dur

    if isinstance(el, chord.Chord):
        # У ABC співзвуччя — це [CEG]; тривалість ставиться після дужки.
        inner = ''.join(pitch_to_abc(p, sharps, measure_state) for p in el.pitches)
        return f'[{inner}]{dur}' + _tie_suffix(el)

    if isinstance(el, note.Note):
        return pitch_to_abc(el.pitch, sharps, measure_state) + dur + _tie_suffix(el)

    return ''


# =================================================================
#  4. Такт
# =================================================================

def _right_barline(m: stream.Measure) -> str:
    """Права тактова риска такту з урахуванням реприз."""
    rb = m.rightBarline
    if rb is None:
        return '|'
    if isinstance(rb, bar.Repeat):
        return ':|'
    return _BARLINE_ABC.get(getattr(rb, 'type', 'regular'), '|')


def _left_repeat(m: stream.Measure) -> str:
    lb = m.leftBarline
    if isinstance(lb, bar.Repeat):
        return '|:'
    return ''


def measure_to_abc(m: stream.Measure, sharps: int, voice_id: Optional[str] = None,
                   with_marks: bool = True) -> str:
    """Один такт однієї партії → рядок ABC (без завершальної риски).

    Якщо в такті є music21-голоси (`stream.Voice`) — беремо той, чий id
    збігається з `voice_id`; так двоголосна права рука не змішується
    в одну кашу. Альтерації скидаються на кожному такті — це вимога і
    нотації, і ABC-парсера.
    """
    measure_state: Dict[Tuple[str, int], int] = {}
    tokens: List[str] = []

    mark = m.getElementsByClass(expressions.RehearsalMark).first() if with_marks else None
    if mark is not None and mark.content:
        # Репетиційна позначка в ABC — це анотація над нотою.
        tokens.append(f'"^{mark.content}"')

    if with_marks:
        mm = m.getElementsByClass(tempo.MetronomeMark).first()
        if mm is not None and mm.number:
            ref = Fraction(mm.referent.quarterLength).limit_denominator(16) / 4
            tokens.append(f'[Q:{ref.numerator}/{ref.denominator}={int(mm.number)}]')

    voices = list(m.getElementsByClass(stream.Voice))
    if voice_id is not None:
        chosen = next((v for v in voices if str(v.id) == str(voice_id)), None)
        if chosen is not None:
            elements = list(chosen.notesAndRests)
        elif voices:
            # Голосу з таким id у цьому такті немає (розділ одноголосний) —
            # заповнюємо паузою, інакше такти двох голосів роз'їдуться.
            elements = []
        else:
            elements = list(m.notesAndRests) if str(voice_id) == '1' else []
    elif voices:
        elements = list(voices[0].notesAndRests)
    else:
        elements = list(m.notesAndRests)

    if not elements:
        # 'x' — НЕВИДИМА пауза: такт вирівняно, але порожній нотоносець
        # не засмічується паузами там, де розділ насправді одноголосний.
        return _left_repeat(m) + 'x' + duration_to_abc(m.barDuration.quarterLength)

    # Акордові символи прив'язуємо до offset: у ABC вони пишуться в лапках
    # ПЕРЕД нотою, до якої належать.
    symbols = {}
    if with_marks:
        for cs in m.getElementsByClass(harmony.ChordSymbol):
            fig = chord_symbol_to_abc(cs)
            if fig:
                symbols.setdefault(round(float(cs.offset), 4), fig)

    for el in sorted(elements, key=lambda e: e.offset):
        piece = element_to_abc(el, sharps, measure_state)
        if not piece:
            continue
        fig = symbols.pop(round(float(el.offset), 4), None)
        tokens.append(f'"{fig}"{piece}' if fig else piece)

    return _left_repeat(m) + ' '.join(tokens)


# =================================================================
#  5. Заголовок партитури
# =================================================================

def _clef_for_part(part: stream.Part) -> str:
    """Ключ нотоносця.

    Беремо явний ключ із партії, але звіряємо його з реальним діапазоном.
    Причина: імпортер ABC у music21 рахує найкращий ключ РАЗОМ із
    висотами акордових символів, а вони лежать низько — і мелодія
    першої октави приїжджає з басовим ключем.
    """
    pitches = [
        p
        for el in part.recurse().notes
        if not isinstance(el, harmony.ChordSymbol)
        for p in el.pitches
    ]
    median_ps = sorted(p.ps for p in pitches)[len(pitches) // 2] if pitches else 60.0

    cl = part.recurse().getElementsByClass(clef.Clef).first()
    if isinstance(cl, clef.AltoClef):
        return 'alto'
    if isinstance(cl, clef.BassClef) and median_ps < 60:
        return 'bass'
    if cl is None or isinstance(cl, clef.BassClef):
        return 'bass' if median_ps < 55 else 'treble'
    return 'treble'


def _key_signature(sc: stream.Score) -> Tuple[int, str]:
    """(кількість дієзів, назва тональності для K:)."""
    ks = sc.recurse().getElementsByClass(key.KeySignature).first()
    sharps = ks.sharps if ks is not None else 0
    return sharps, _MAJOR_BY_SHARPS.get(sharps, 'C')


def _meter_string(sc: stream.Score) -> str:
    ts = sc.recurse().getElementsByClass(meter.TimeSignature).first()
    return ts.ratioString if ts is not None else '4/4'


def _tempo_line(sc: stream.Score) -> str:
    mm = sc.recurse().getElementsByClass(tempo.MetronomeMark).first()
    if mm is None or not mm.number:
        return ''
    ref = Fraction(mm.referent.quarterLength).limit_denominator(16) / 4
    return f'Q:{ref.numerator}/{ref.denominator}={int(mm.number)}\n'


def build_header(sc: stream.Score, title: str, staves: List[List[Tuple[str, str]]]) -> str:
    """Складає блок заголовків ABC.

    `staves` — список нотоносців, кожен з яких є списком (id голосу, ключ).
    Директива %%score змушує abcjs малювати акколаду замість двох
    незалежних систем; голоси одного нотоносця беруться в дужки:
    `%%score {(1 2) | 3}` — два голоси на верхньому стані, один на нижньому.
    """
    _sharps, key_name = _key_signature(sc)
    lines = [
        'X:1',
        f'T:{title}',
        f'M:{_meter_string(sc)}',
        f'L:{UNIT_LENGTH.numerator}/{UNIT_LENGTH.denominator}',
    ]
    tempo_line = _tempo_line(sc)
    if tempo_line:
        lines.append(tempo_line.rstrip('\n'))

    if len(staves) > 1 or any(len(s) > 1 for s in staves):
        groups = []
        for staff in staves:
            ids = ' '.join(vid for vid, _ in staff)
            groups.append(f'({ids})' if len(staff) > 1 else ids)
        lines.append('%%score {' + ' | '.join(groups) + '}')

    lines.append(f'K:{key_name}')
    for staff in staves:
        for vid, clef_name in staff:
            lines.append(f'V:{vid} clef={clef_name}')

    return '\n'.join(lines) + '\n'


# =================================================================
#  6. Головна функція
# =================================================================

BARS_PER_LINE = 4


def score_to_abc(sc: stream.Score, title: str = 'HymnArranger') -> str:
    """Партитура music21 → рядок ABC, готовий для abcjs.

    Голоси виводяться блоками по кілька тактів і чергуються
    (`V:1` … `V:2` … `V:1` …). abcjs вирівнює їх по номеру такту, тож
    права і ліва руки стають на одну акколаду.
    """
    parts = list(sc.parts) if hasattr(sc, 'parts') else [sc]
    if not parts:
        return build_header(sc, title, [('1', 'treble')])

    sharps, _ = _key_signature(sc)

    # (id голосу, ключ, такти партії, який music21-Voice брати)
    # Голоси шукаємо ПО ВСІХ тактах, а не лише по першому: у сюїті
    # двоголосний розділ може стояти сьомим, і тоді перевірка першого
    # такту мовчки викидає другий голос.
    voice_plan: List[Tuple[str, str, List[stream.Measure], Optional[str]]] = []
    staves: List[List[Tuple[str, str]]] = []
    counter = 1
    for part in parts:
        measures = list(part.getElementsByClass(stream.Measure))
        if not measures:
            continue
        clef_name = _clef_for_part(part)
        inner_ids: List[str] = []
        for m in measures:
            for v in m.getElementsByClass(stream.Voice):
                if str(v.id) not in inner_ids:
                    inner_ids.append(str(v.id))

        staff: List[Tuple[str, str]] = []
        if len(inner_ids) > 1:
            for vid in inner_ids:
                voice_plan.append((str(counter), clef_name, measures, vid))
                staff.append((str(counter), clef_name))
                counter += 1
        else:
            voice_plan.append((str(counter), clef_name, measures, None))
            staff.append((str(counter), clef_name))
            counter += 1
        staves.append(staff)

    header = build_header(sc, title, staves)

    total = max(len(ms) for _, _, ms, _ in voice_plan)
    body: List[str] = []

    for start in range(0, total, BARS_PER_LINE):
        stop = min(start + BARS_PER_LINE, total)
        for pos, (vid, _clef_name, measures, inner_id) in enumerate(voice_plan):
            chunk: List[str] = []
            for i in range(start, stop):
                if i >= len(measures):
                    continue
                m = measures[i]
                # Репетиційну позначку друкуємо лише над найвищим голосом,
                # інакше вона дублюється на кожному нотоносці.
                chunk.append(measure_to_abc(m, sharps, inner_id, with_marks=(pos == 0)))
                chunk.append(_right_barline(m))
            if chunk:
                body.append(f'[V:{vid}] ' + ' '.join(chunk))

    return header + '\n'.join(body) + '\n'