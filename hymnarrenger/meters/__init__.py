"""Все, що залежить від РОЗМІРУ, зібрано тут і більше ніде.

Два сімейства:
  simple    — 2/4, 3/4, 4/4 і взагалі будь-який розмір із дводольною долею
  compound  — 6/8, 9/8, 12/8: доля дорівнює чвертці з крапкою (1.5)

Приналежність визначається не за чисельником, а за `beatDuration`:
music21 уже вміє це рахувати, тож 3/8 чи 15/8 підуть правильним шляхом
без жодного окремого рядка коду.

Модулі нижче експортують однаковий набір імен, тому решта пакета
працює з розміром через один інтерфейс.
"""

from __future__ import annotations

from typing import List, Tuple

from music21 import meter

COMPOUND_BEAT_QL = 1.5

# Прості (непунктирні) тривалості. Саме вони мають виходити при
# дробленні: пунктирна частка на кшталт 0.375 всередині чвертки
# з крапкою дає відчуття "чотири проти трьох" і ламає тридольність.
_PLAIN = (4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625)
# Пунктирні — запасний варіант, якщо простого дільника не існує.
_DOTTED = (3.0, 1.5, 0.75, 0.375, 0.1875)


def is_compound(ts: meter.TimeSignature) -> bool:
    """Чи є доля тридольною (чвертка з крапкою)."""
    try:
        return abs(ts.beatDuration.quarterLength - COMPOUND_BEAT_QL) < 1e-6
    except Exception:
        return ts.denominator == 8 and ts.numerator % 3 == 0


def family(ts: meter.TimeSignature):
    from . import simple as _simple
    from . import compound as _compound
    return _compound if is_compound(ts) else _simple


def _fits(ql: float, allowed) -> bool:
    return any(abs(ql - x) < 1e-6 for x in allowed)


def parts_for(note_ql: float, unit_ql: float, cap: int) -> int:
    """
    На скільки частин ділити ноту тривалістю note_ql, прагнучи до unit_ql.

    Стеля cap НЕ обрізає арифметично. Обрізання "скільки вийшло, але не
    більше cap" давало для чвертки з крапкою 4 частини по 0.375 —
    пунктирні шістнадцяті, яких у фактурі бути не повинно. Замість цього
    беремо найбільший ДОПУСТИМИЙ дільник: такий, при якому частка
    лишається нотованою тривалістю.
    """
    if unit_ql <= 0 or note_ql <= 0:
        return 1
    start = int(note_ql / unit_ql + 1e-6)
    if start < 1:
        return 1
    for allowed in (_PLAIN, _PLAIN + _DOTTED):
        n = start
        while n > 1:
            if n <= cap and _fits(note_ql / n, allowed):
                return n
            n -= 1
    return 1


def lh_pattern_for(ts: meter.TimeSignature, cfg) -> Tuple[float, List[str]]:
    beat_ql, pat = family(ts).lh_pattern_for(ts, cfg)
    bar_ql = ts.barDuration.quarterLength
    assert abs(beat_ql * len(pat) - bar_ql) < 1e-6, \
        f'патерн {pat} не вкладається в такт {ts.ratioString}'
    return beat_ql, pat


def presets(ts: meter.TimeSignature):
    return family(ts).presets()


def suite_plan(ts: meter.TimeSignature):
    return family(ts).suite_plan()


def lh_pool(ts: meter.TimeSignature):
    return family(ts).LH_POOL


def bass_led(ts: meter.TimeSignature):
    return family(ts).BASS_LED
