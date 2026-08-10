"""Ядро обігравання мелодії.

Два інваріанти, яких figurate() не порушує ніколи:
  1. slot 0 = нота мелодії (сильна доля лишається впізнаваною);
  2. жодна нота фігури не дорівнює наступній ноті мелодії
     і жодні дві сусідні ноти не однакові.
"""

from __future__ import annotations

from typing import Optional, List

from music21 import key, note, pitch

from .model import ArrangeContext, ArrangeConfig
from .theory import (
    _step, _steps_between, _chord_tones_near, _nearest_chord_tone,
    _chord_tone_between, _approach_tone, _clamp,
)
from .meters import parts_for


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
            # parts_for знає про тридольність і не породжує 0.375
            n_parts = parts_for(ev.ql, unit, cfg.max_parts)

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
