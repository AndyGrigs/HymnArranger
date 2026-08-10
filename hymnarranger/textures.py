"""Фактури правої руки, відмінні від обігравання.

Кожна виведена з нотного прикладу і відтворює його з точністю до ноти:
  build_melody_plain   — чисте проведення теми
  build_chord_melody   — акордова мелодія (мелодія зверху + октава знизу)
  build_pulse_hand     — відбиття ритму: тризвуки / поодинокі / пауза-нота-двозвук
  build_two_voice_arp  — два голоси: мелодія + безперервне арпеджіо
  build_thirds_hand    — витримані терції й сексти до мелодії в басі
  build_bass_melody    — мелодія, перенесена в басовий регістр
"""

from __future__ import annotations

from typing import Optional, List

from music21 import chord, key, note, pitch

from .model import ArrangeContext, ArrangeConfig
from .theory import _step, _chord_tones_from, _clamp
from .meters import parts_for, is_compound


def build_melody_plain(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 3а — чисте проведення теми.
    Мелодія не змінюється взагалі; сенс у тому, щоб слухач почув тему
    цілком, перш ніж вона піде у варіації.
    """
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            el = note.Rest()
        else:
            p = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
            el = note.Note(_clamp(pitch.Pitch(p.nameWithOctave), cfg))
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        out.append(el)
    return out


def build_chord_melody(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 1 — акордова мелодія.
    Мелодія лишається верхнім голосом; знизу вона дублюється на октаву,
    а два вільні місця між ними заповнюються рештою тонів акорду.
    """
    # акордова мелодія дублює тему НА ОКТАВУ ВНИЗ, тож для гімну, записаного
    # низько, нижній голос вилітає під праву клавіатуру. Підбираємо зсув так,
    # щоб найнижчий тон акорду лишався в межах інструмента.
    shift = cfg.octave_shift
    lows = [e.pitch.midi for e in ctx.events if not e.is_rest]
    if lows:
        while min(lows) + 12 * shift - 12 < cfg.rh_min_midi:
            shift += 1

    out = []
    for ev in ctx.events:
        if ev.is_rest:
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
            out.append(r); continue
        if ctx.in_pickup(ev.offset):
            n = note.Note(ev.pitch); n.duration.quarterLength = ev.ql
            n.offset = ev.offset; out.append(n); continue

        top = ev.pitch.transpose(12 * shift) if shift else ev.pitch
        cs = ctx.chord_at(ev.offset)
        bottom = top.transpose(-12)
        inner = [p for p in _chord_tones_from(cs, bottom, 8, ctx.key)
                 if bottom.midi < p.midi < top.midi][:2]
        pitches = [bottom] + inner + [top]
        c = chord.Chord(sorted(set(p.nameWithOctave for p in pitches),
                              key=lambda s: pitch.Pitch(s).midi))
        c.duration.quarterLength = ev.ql
        c.offset = ev.offset
        out.append(c)
    return out


def _bass_shift(ctx: ArrangeContext, cfg: ArrangeConfig) -> int:
    """
    Скільки октав опустити мелодію в бас. Фіксоване число ламається,
    щойно вхідний гімн записано в іншій октаві: те саме -2 давало C3 на
    одному матеріалі і C2 на іншому. Тому прив'язуємось до РЕГІСТРУ:
    найнижча нота мелодії має лягти приблизно на bass_target_midi.
    """
    if cfg.bass_melody_octaves is not None:
        return cfg.bass_melody_octaves
    lows = [e.pitch.midi for e in ctx.events if not e.is_rest]
    if not lows:
        return -1
    return int(round((cfg.bass_target_midi - min(lows)) / 12.0))


def build_pulse_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАДИ 2б / 2в — права рука відбиває ритм.
    На кожну ноту мелодії: пауза на сильній частці + (pulse_parts-1) ударів.
    'single' — поодинокі тони акорду за схемою верх-низ-верх;
    'chords' — тризвук у тісному розташуванні, що йде за мелодією.
    """
    triads = (cfg.mode == 'bass_melody_chords')
    dyad = (cfg.mode == 'bass_melody_dyad')
    shift = _bass_shift(ctx, cfg)
    out = []
    for ev in ctx.events:
        if ev.is_rest or ctx.in_pickup(ev.offset):
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
            out.append(r); continue

        cs = ctx.chord_at(ev.offset)
        # кількість ударів виводиться з ТРИВАЛОСТІ ноти, а не фіксована:
        # саме це відрізняє приклад 2а (вісімки) від 2в (шістнадцяті)
        n_parts = max(2, parts_for(ev.ql, cfg.pulse_unit_ql, cfg.max_parts))
        sub = ev.ql / n_parts

        # У режимі "пауза-нота-двозвук" паузи на початку долі зливаються
        # в одну (дві шістнадцяті -> вісімкова), інакше нотний текст рябіє.
        # Якщо часток лише дві (коротка нота мелодії), нижньої ноти немає:
        # фігура скорочується до "пауза + двозвук". Інакше пауза виходила
        # нульової тривалості й партитура ставала невалідною.
        short_dyad = dyad and n_parts < 3
        rest_ql = sub if (not dyad or short_dyad) else sub * (n_parts - 2)
        if rest_ql > 1e-9:
            r = note.Rest(); r.duration.quarterLength = rest_ql; r.offset = ev.offset
            out.append(r)

        # мелодія вже звучить у басу; права рука сидить над нею,
        # але не нижче підлоги регістру
        bass = ev.pitch.transpose(12 * shift)
        floor = pitch.Pitch(midi=max(cfg.pulse_floor_midi, bass.midi + 12))

        if dyad:
            # ПРИКЛАД 2б_new: [пауза, пауза, нижня нота, двозвук]
            low = _chord_tones_from(cs, floor, 1, ctx.key)[0]
            highs = _chord_tones_from(cs, pitch.Pitch(midi=low.midi + 1), 2, ctx.key)
            # вступна пауза вже додана вище, тож тут лишається n_parts-1 позицій
            base = ev.offset + rest_ql
            n2 = chord.Chord([p.nameWithOctave for p in highs])
            if short_dyad:
                n2.duration.quarterLength = ev.ql - rest_ql
                n2.offset = base
                out.append(n2)
            else:
                n1 = note.Note(low)
                n1.duration.quarterLength = sub; n1.offset = base
                n2.duration.quarterLength = sub; n2.offset = base + sub
                out.extend([n1, n2])
        elif triads:
            voicing = _chord_tones_from(cs, floor, 3, ctx.key)
            for j in range(1, n_parts):
                c = chord.Chord([p.nameWithOctave for p in voicing])
                c.duration.quarterLength = sub
                c.offset = ev.offset + j * sub
                out.append(c)
        else:
            low = _chord_tones_from(cs, floor, 1, ctx.key)[0]
            # верхні тони — наступні тони акорду СТРОГО вище нижнього
            highs = _chord_tones_from(cs, pitch.Pitch(midi=low.midi + 1), 4, ctx.key)
            seq = []
            hi = 0
            for j in range(1, n_parts):
                if j % 2 == 1:
                    seq.append(highs[hi % len(highs)]); hi += 1
                else:
                    seq.append(low)
            for j, p in enumerate(seq, start=1):
                nn = note.Note(p)
                nn.duration.quarterLength = sub
                nn.offset = ev.offset + j * sub
                out.append(nn)
    return out


def build_bass_melody(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """Ліва рука для режимів 2б/2в: мелодія, перенесена в басовий регістр."""
    shift = 12 * _bass_shift(ctx, cfg)
    out = []
    for ev in ctx.events:
        if ev.is_rest:
            r = note.Rest(); r.duration.quarterLength = ev.ql; r.offset = ev.offset
        else:
            r = note.Note(ev.pitch.transpose(shift))
            r.duration.quarterLength = ev.ql
        r.offset = ev.offset
        out.append(r)
    return out


def build_two_voice_arp(ctx: ArrangeContext, cfg: ArrangeConfig):
    """
    ПРИКЛАД 4а — два самостійні голоси на одному нотоносці.
      голос 2: мелодія без змін (довгі тривалості);
      голос 1: безперервне арпеджіо шістнадцятими.

    Фігура будується від ноти мелодії вгору по тонах акорду і назад:
    C4 -> E4 -> G4 -> E4. На відміну від інших режимів дроблення тут
    прив'язане до ДОЛІ, а не до тривалості ноти: витримана половинна
    все одно отримує рівний рух шістнадцятими.
    """
    beat_ql = ctx.ts.beatDuration.quarterLength
    n_arp = max(2, parts_for(beat_ql, cfg.arp_unit_ql, 16))
    shape = cfg.arp_shape

    # голос 2 — мелодія як є
    voice_mel = []
    for ev in ctx.events:
        el = note.Rest() if ev.is_rest else note.Note(ev.pitch)
        el.duration.quarterLength = ev.ql
        el.offset = ev.offset
        voice_mel.append(el)

    # мелодія, що звучить на кожній долі
    def sounding(off):
        cur = None
        for ev in ctx.events:
            if ev.offset <= off + 1e-6 < ev.offset + ev.ql:
                cur = ev
        return cur

    voice_arp = []
    off = 0.0
    while off < ctx.total_ql - 1e-6:
        ev = sounding(off)
        if ev is None or ev.is_rest or ctx.in_pickup(off):
            r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = off
            voice_arp.append(r); off += beat_ql; continue

        cs = ctx.chord_at(off)
        start = ev.pitch.transpose(12 * cfg.octave_shift) if cfg.octave_shift else ev.pitch
        tones = _chord_tones_from(cs, start, max(shape) + 3, ctx.key)
        # Фігура ЗАВЖДИ стартує з ноти мелодії — саме це робить фактуру
        # двоголосою на слух. Якщо нота мелодії не входить в акорд
        # (наприклад до під G7), вона все одно лишається першою,
        # а далі йдуть тони акорду над нею.
        above = [t for t in tones if t.midi > start.midi]
        tones = [pitch.Pitch(start.nameWithOctave)] + above
        while len(tones) < max(shape) + 1:
            tones.append(tones[-1].transpose(12))

        sub = beat_ql / n_arp
        for j in range(n_arp):
            idx = shape[j % len(shape)]
            p = tones[min(idx, len(tones) - 1)]
            nn = note.Note(_clamp(pitch.Pitch(p.nameWithOctave), cfg))
            nn.duration.quarterLength = sub
            nn.offset = off + j * sub
            voice_arp.append(nn)
        off += beat_ql

    return (voice_arp, voice_mel)


def build_thirds_hand(ctx: ArrangeContext, cfg: ArrangeConfig) -> List[note.GeneralNote]:
    """
    ПРИКЛАД 2г — мелодію веде бас, права рука вступає після паузи
    і тримає ВИТРИМАНІ ноти, що утворюють з басом терцію або сексту.

    Інші інтервали (октава, квінта, секунда) відкидаються свідомо:
    саме терції й сексти дають той повний, "хоровий" призвук, заради
    якого ця фактура й існує. Серед допустимих перевага надається
    тонам активного акорду і найменшому руху від попередньої ноти.
    """
    beat_ql = ctx.ts.beatDuration.quarterLength
    shift = _bass_shift(ctx, cfg)
    CONSONANT = (3, 4, 8, 9)          # м3, в3, м6, в6

    segs = [(e.offset, e.offset + e.ql, e.pitch.transpose(12 * shift))
            for e in ctx.events if not e.is_rest]

    def under(off, dur):
        return [g for g in segs if off < g[1] - 1e-6 and g[0] < off + dur - 1e-6]

    def candidates(bass_list, cs):
        """Висоти, що дають терцію/сексту до КОЖНОГО баса у вікні."""
        chord_pcs = {p.pitchClass for p in cs.pitches} if cs is not None else set()
        out = []
        for semis in CONSONANT:
            for octv in (0, 12, 24):
                p = bass_list[0][2].transpose(semis + octv)
                if p.midi < cfg.thirds_floor_midi or p.midi > cfg.rh_max_midi:
                    continue
                if all((p.midi - g[2].midi) % 12 in CONSONANT for g in bass_list):
                    out.append((0 if (not chord_pcs or p.pitchClass in chord_pcs) else 1, p))
        return out

    out: List[note.GeneralNote] = []
    r = note.Rest(); r.duration.quarterLength = beat_ql; r.offset = 0.0
    out.append(r)                                    # обов'язковий вступ з паузи

    prev = None
    off = beat_ql
    first = True
    while off < ctx.total_ql - 1e-6:
        # тривалість супроводу задана В ДОЛЯХ: 2 долі = 2.0 у простих
        # розмірах і 3.0 у тридольних, тобто цілий такт 6/8
        hold = cfg.thirds_note_beats * beat_ql
        dur = min(beat_ql if first else hold, ctx.total_ql - off)

        # Якщо під витриманою нотою бас змінюється так, що спільної
        # терції/сексти не існує, КОРОТШАЄМО ноту до зміни баса.
        # Інакше правило "тільки терція або секста" було б порушене.
        pool = []
        while dur > 1e-6:
            bl = under(off, dur)
            if not bl:
                break
            pool = candidates(bl, ctx.chord_at(off))
            if pool:
                break
            nxt = min(g[1] for g in bl if g[1] > off + 1e-6)
            dur = nxt - off

        if not pool:
            el = note.Rest()
        else:
            rank = min(r0 for r0, _ in pool)
            best = [p for r0, p in pool if r0 == rank]
            if prev is None:
                target = cfg.thirds_floor_midi + 2
                p = min(best, key=lambda x: abs(x.midi - target))
            else:
                p = min(best, key=lambda x: (abs(x.midi - prev.midi), x.midi))
            prev = p
            el = note.Note(p)
        el.duration.quarterLength = dur
        el.offset = off
        out.append(el)
        off += dur
        first = False

    # Коли бас рухається дрібно, ноту супроводу доводиться перевибирати
    # часто, і поруч опиняються дві однакові висоти. Зливаємо їх в одну
    # витриману — фактура має звучати як педаль, а не як повтори.
    merged: List[note.GeneralNote] = []
    for el in out:
        if merged and not el.isRest and not merged[-1].isRest \
                and merged[-1].pitches[0].nameWithOctave == el.pitches[0].nameWithOctave \
                and abs(merged[-1].offset + merged[-1].duration.quarterLength
                        - el.offset) < 1e-6:
            merged[-1].duration.quarterLength += el.duration.quarterLength
        elif merged and el.isRest and merged[-1].isRest \
                and abs(merged[-1].offset + merged[-1].duration.quarterLength
                        - el.offset) < 1e-6:
            merged[-1].duration.quarterLength += el.duration.quarterLength
        else:
            merged.append(el)
    return merged