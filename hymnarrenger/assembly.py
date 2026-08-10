"""Шар 3 — складання партитури: такти, ключі, затакт, голоси, склейка."""

from __future__ import annotations

import copy
from typing import Optional, List

from music21 import (
    stream, note, chord, clef, key, meter, layout, tempo, expressions, bar,
)

from .model import ArrangeContext, ArrangeConfig
from .parsing import parse_input
from .figuration import build_right_hand
from .textures import (
    build_melody_plain, build_chord_melody, build_pulse_hand,
    build_bass_melody, build_two_voice_arp, build_thirds_hand,
)
from ..lefthand import build_left_hand


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
                  cfgs: Optional[List[ArrangeConfig]] = None,
                  preset_map=None) -> stream.Score:
    """
    Склеює кілька варіантів аранжування в ОДНУ партитуру, послідовно.
    Кожен варіант отримує репетиційну позначку зі своєю назвою і
    відокремлюється подвійною тактовою рискою — зручно і для порівняння
    на слух, і як ілюстрація до розділу 4 дипломної роботи.
    """
    if cfgs is None:
        if preset_map is None:
            from .meters import presets as _p
            preset_map = _p(parse_input(source).ts)
        names = presets or list(preset_map)
        cfgs = [preset_map[n] for n in names]

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


def to_musicxml_string(sc: stream.Score) -> str:
    from music21.musicxml.m21ToXml import GeneralObjectExporter
    return GeneralObjectExporter(sc).parse().decode('utf-8')
