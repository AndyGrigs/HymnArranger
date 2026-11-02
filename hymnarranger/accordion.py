"""Збірка двостанної партитури баяна з ABC правої та лівої руки."""
import os
import tempfile

import music21
from music21 import clef, instrument, stream

from hymnarranger.assembly import to_musicxml_string


class EmptyHandError(ValueError):
    """У жодній з рук немає жодної ноти."""


def _parse_hand(body: str, key: str, meter: str) -> stream.Part:
    # Басовий ключ у ABC music21 зсуває октаву на дві вниз, тому читаємо
    # обидві руки як скрипкові, а ключ лівої виставляємо вже після розбору.
    abc = f'X:1\nT:t\nM:{meter}\nL:1/8\nK:{key}\n{body}\n'
    fd, path = tempfile.mkstemp(suffix='.abc')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(abc)
        parsed = music21.converter.parse(path)
    finally:
        os.unlink(path)
    return parsed.parts[0]


def build_accordion_musicxml(right: str, left: str, key: str = 'C', meter: str = '4/4') -> str:
    """Права рука → скрипковий ключ, ліва → басовий; обидві — одна партитура."""
    if not right.strip() and not left.strip():
        raise EmptyHandError('Партитура порожня')

    score = stream.Score()
    for body, bass in ((right, False), (left, True)):
        part = _parse_hand(body or 'z8 |]', key, meter)
        if bass:
            for c in list(part.recurse().getElementsByClass(clef.Clef)):
                c.activeSite.remove(c)
            first = part.getElementsByClass(stream.Measure).first()
            (first if first is not None else part).insert(0, clef.BassClef())
        part.partName = 'Accordion R' if not bass else 'Accordion L'
        part.insert(0, instrument.Accordion())
        score.insert(0, part)
    return to_musicxml_string(score)
