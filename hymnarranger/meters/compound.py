"""Тридольна доля: 6/8, 9/8, 12/8.

Головна відмінність від дводольних розмірів — вісімка тут НЕ доля.
Доля дорівнює чвертці з крапкою і ділиться на три, тому:

  * патерн лівої руки має лягати групами по три вісімки, інакше бас
    опиняється всередині групи й ритм "розвалюється";
  * обігравання природно дає 3 або 6 нот на долю, а не 2 чи 4;
  * фігурою тут працює АРПЕДЖІО: тридольна група з трьох тонів акорду
    звучить природно, тоді як оспівування допоміжними тонами
    у швидкому тридольному русі перетворюється на трель.
"""

from __future__ import annotations

from typing import List, Tuple

from music21 import meter

from ..model import ArrangeConfig


# ---------------------------------------------------------------- ліва рука

def lh_pattern_for(ts: meter.TimeSignature, cfg) -> Tuple[float, List[str]]:
    """
    'B' — основний бас, 'F' — допоміжний (квінта вгору), 'A' — акорд.

    compound_march  Б А А | Б А А     бас на кожній групі: рахунок 1-2-3 1-2-3
    compound_alt    Б А А | К А А     бас чергується з квінтою по групах
    compound_beat   Б(1.5) А(1.5)     бас і акорд чвертками з крапкою по долях
    """
    bar_ql = ts.barDuration.quarterLength
    groups = max(1, int(round(bar_ql / 1.5)))
    p = cfg.lh_pattern

    if p == 'compound_beat':
        # Одна подія на долю: бас, далі акорди. Розподіл ролей той самий,
        # що й у простих розмірах: 2 долі -> Б А, 3 -> Б А А, 4 -> Б А К А.
        if groups >= 4:
            pat = ['B', 'A', 'F', 'A'] + ['A'] * (groups - 4)
        elif groups == 3:
            pat = ['B', 'A', 'A']
        elif groups == 2:
            pat = ['B', 'A']
        else:
            pat = ['B']
        return 1.5, pat

    if p == 'compound_march':
        pat = []
        for _ in range(groups):
            pat += ['B', 'A', 'A']
        return 0.5, pat

    # 'compound_alt', 'auto' і будь-що інше: бас чергується з квінтою
    pat = []
    for g in range(groups):
        pat += ['B' if g % 2 == 0 else 'F', 'A', 'A']
    return 0.5, pat


LH_PATTERNS = ('compound_march', 'compound_alt', 'compound_beat', 'auto')

# Патерни, серед яких сюїта тасує супровід по розділах
LH_POOL = ('compound_march', 'compound_alt', 'compound_beat')


# ---------------------------------------------------------------- пресети

def presets():
    return {
        'theme': ArrangeConfig(
            mode='melody_plain', lh_pattern='compound_beat',
            name='Тема'),

        # Обігравання вісімками = три ноти на долю. Фігура — арпеджіо,
        # бо саме розкладений акорд лягає на тридольну групу.
        'eighths_arp': ArrangeConfig(
            unit_ql=0.5, tight_figure='arpeggio', max_parts=6,
            lh_pattern='compound_march',
            name='Оспівування арпеджіо (вісімки)'),

        # Шістнадцяті — шість нот на долю, теж арпеджіо.
        'sixteenths_arp': ArrangeConfig(
            unit_ql=0.25, tight_figure='arpeggio', max_parts=12,
            lh_pattern='compound_march',
            name='Шістнадцяті арпеджіо'),

        'two_voice_arp': ArrangeConfig(
            mode='two_voice_arp', arp_shape=(0, 1, 2),
            lh_pattern='compound_beat',
            name='Два голоси: мелодія + арпеджіо'),

        'bass_chords': ArrangeConfig(
            mode='bass_melody_chords', pulse_floor_midi=64,
            pulse_unit_ql=0.5, max_parts=3,
            name='Мелодія в басі / тризвуки'),
        'bass_single': ArrangeConfig(
            mode='bass_melody_dyad', pulse_floor_midi=67,
            pulse_unit_ql=0.5, max_parts=3,
            name='Мелодія в басі / пауза-нота-двозвук'),
        'bass_thirds': ArrangeConfig(
            mode='bass_melody_thirds',
            name='Мелодія в басі / терції-сексти'),

        'chord_melody_8va': ArrangeConfig(
            mode='chord_melody', octave_shift=1, rh_max_midi=100,
            lh_pattern='compound_beat',
            name='Акордова мелодія (октавою вище)'),
    }


# Розділ, де мелодію веде ліва рука: тільки терції й сексти.
BASS_LED = 'bass_thirds'


def suite_plan():
    return [
        'theme',              # 1. тема з басом
        'eighths_arp',        # 2. оспівування мелодії арпеджіо
        'sixteenths_arp',     # 3. те саме дрібніше, теж арпеджіо
        BASS_LED,             # 4. мелодію веде ліва рука
        'two_voice_arp',      # 5. два голоси
        'chord_melody_8va',   # 6. фінал акордами
    ]