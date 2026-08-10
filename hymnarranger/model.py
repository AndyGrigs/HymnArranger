"""Проміжна модель даних: події мелодії, контекст твору, конфіг аранжування."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from music21 import harmony, key, meter, pitch


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


SECOND_STRATEGIES = ('chord_tone', 'neighbor_away')


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
    thirds_note_beats: float = 2.0    # тривалість ноти супроводу В ДОЛЯХ (2г)
    tempo: Optional[int] = None
    instrument_name: str = 'Accordion'
    name: str = 'default'
