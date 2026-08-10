"""Музичні примітиви: діатонічні кроки, тони акорду, ввідні тони, регістр.

Усі функції тут ЧИСТІ: вхід -> вихід, без стану. Саме тому їх можна
масово прогнати регресією і зловити помилку на кшталт хроматичного
зсуву в мінорі, не запускаючи весь конвеєр.
"""

from __future__ import annotations

from typing import Optional, List

from music21 import key, pitch

from .model import ArrangeConfig


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

def _clamp(p: pitch.Pitch, cfg: ArrangeConfig) -> pitch.Pitch:
    while p.midi < cfg.rh_min_midi:
        p = p.transpose(12)
    while p.midi > cfg.rh_max_midi:
        p = p.transpose(-12)
    return p
