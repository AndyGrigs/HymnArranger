"""Дводольна доля: 2/4, 3/4, 4/4 — усе, що працювало досі.

Логіка не змінена: цей модуль існує, щоб тридольні розміри не тягли
за собою умовних гілок усередині спільного коду.
"""

from __future__ import annotations

from typing import List, Tuple

from music21 import meter

from ..model import ArrangeConfig


def lh_pattern_for(ts: meter.TimeSignature, cfg) -> Tuple[float, List[str]]:
    """
    (тривалість одного удару, послідовність 'B'/'F'/'A' на ОДИН такт).
    Інваріант: beat_ql * len(pattern) == довжина такту. Інакше ліва рука
    "поїде" відносно правої — саме це й ламало пресет 'waltz' у 4/4.
    """
    num, den = ts.numerator, ts.denominator
    bar_ql = ts.barDuration.quarterLength
    p = cfg.lh_pattern

    if p in ('eighth_march', 'eighth_alt'):
        # вісімковий пульс: 8 позицій у 4/4, 6 у 3/4, 4 у 2/4
        n_slots = int(round(bar_ql / 0.5))
        if p == 'eighth_alt':                          # Б А К А Б А К А
            pat = [('B' if (i // 2) % 2 == 0 else 'F') if i % 2 == 0 else 'A'
                   for i in range(n_slots)]
        else:                                          # Б А А А К А А А
            half = n_slots // 2
            pat = []
            for i in range(n_slots):
                if i == 0:
                    pat.append('B')
                elif half and i == half:
                    pat.append('F')
                else:
                    pat.append('A')
        return 0.5, pat

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


LH_PATTERNS = ('bass_chord', 'bass_alt_fifth', 'waltz', 'auto',
               'eighth_march', 'eighth_alt')

LH_POOL = ('auto', 'bass_chord', 'bass_alt_fifth', 'eighth_march', 'eighth_alt')


def presets():
    return {
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


# Розділ, де мелодію веде ліва рука. Лишилася одна фактура:
# права рука в терцію/сексту до баса — вона єдина не глушить мелодію.
BASS_LED = 'bass_thirds'


def suite_plan():
    return [
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