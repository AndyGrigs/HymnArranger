"""Шар 1 — читання MusicXML і побудова ArrangeContext з АБСОЛЮТНИМИ offset'ами."""

from __future__ import annotations

import re
from typing import Optional, List, Tuple

from music21 import (
    stream, harmony, key, meter, converter, expressions,
)

from .model import MelodyEvent, ArrangeContext


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
        elif m0.number == 0 and filled < bar_ql - 1e-6:
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
