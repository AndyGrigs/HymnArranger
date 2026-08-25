"""Unit tests for pure-function modules: theory.py and meters.parts_for.

These tests do not touch FastAPI or the file system — they exercise only
stateless helpers that take music21 objects and return music21 objects.
"""

from music21 import harmony, key, pitch

from hymnarranger.meters import parts_for
from hymnarranger.parsing import parse_input
from hymnarranger.theory import _approach_tone, _chord_tones_near, _step, _steps_between

# ── _step ─────────────────────────────────────────────────────────────────────

def test_step_up_whole_step():
    assert _step(pitch.Pitch("C5"), key.Key("C"), 1).name == "D"


def test_step_up_half_step_at_mi_fa():
    assert _step(pitch.Pitch("E5"), key.Key("C"), 1).name == "F"


def test_step_down_crosses_octave_boundary():
    result = _step(pitch.Pitch("C5"), key.Key("C"), -1)
    assert result.name == "B"
    assert result.octave == 4


def test_step_up_leading_tone_resolves_to_tonic():
    result = _step(pitch.Pitch("B4"), key.Key("C"), 1)
    assert result.name == "C"


def test_step_down_in_sharp_key_uses_key_signature():
    # In G major, the step below F# is E (not F-natural).
    result = _step(pitch.Pitch("F#5"), key.Key("G"), -1)
    assert result.name == "E"


# ── _steps_between ────────────────────────────────────────────────────────────

def test_steps_between_unison_is_zero():
    k = key.Key("C")
    assert _steps_between(pitch.Pitch("C5"), pitch.Pitch("C5"), k) == 0


def test_steps_between_diatonic_third_upward():
    k = key.Key("C")
    # C → D → E: 2 diatonic steps upward
    assert _steps_between(pitch.Pitch("C5"), pitch.Pitch("E5"), k) == 2


def test_steps_between_diatonic_third_downward():
    k = key.Key("C")
    assert _steps_between(pitch.Pitch("E5"), pitch.Pitch("C5"), k) == -2


def test_steps_between_honours_cap():
    k = key.Key("C")
    # Two octaves apart; with cap=3 we should never get more than 3
    result = _steps_between(pitch.Pitch("C4"), pitch.Pitch("C6"), k, cap=3)
    assert abs(result) <= 3


# ── _chord_tones_near ─────────────────────────────────────────────────────────

def test_chord_tones_near_c_major_triad():
    cs = harmony.ChordSymbol("C")
    ref = pitch.Pitch("C5")
    names = {p.name for p in _chord_tones_near(cs, ref)}
    assert {"C", "E", "G"}.issubset(names)


def test_chord_tones_near_none_returns_empty():
    assert _chord_tones_near(None, pitch.Pitch("C5")) == []


def test_chord_tones_near_pitches_span_three_octaves_around_ref():
    cs = harmony.ChordSymbol("G")
    ref = pitch.Pitch("G5")
    tones = _chord_tones_near(cs, ref)
    # The function puts each chord tone in ref.octave-1, ref.octave, ref.octave+1
    assert all(ref.octave - 1 <= p.octave <= ref.octave + 1 for p in tones)


def test_chord_tones_near_result_is_sorted_by_midi():
    cs = harmony.ChordSymbol("Am")
    ref = pitch.Pitch("A4")
    tones = _chord_tones_near(cs, ref)
    midis = [p.midi for p in tones]
    assert midis == sorted(midis)


# ── _approach_tone ────────────────────────────────────────────────────────────

def test_approach_tone_from_below_is_step_below_target():
    k = key.Key("C")
    # Approaching E5 from below (C5) → one step below E5 = D5
    result = _approach_tone(pitch.Pitch("E5"), pitch.Pitch("C5"), k)
    assert result.midi == pitch.Pitch("D5").midi


def test_approach_tone_from_above_is_step_above_target():
    k = key.Key("C")
    # Approaching G5 from above (B5) → one step above G5 = A5
    result = _approach_tone(pitch.Pitch("G5"), pitch.Pitch("B5"), k)
    assert result.midi == pitch.Pitch("A5").midi


def test_approach_tone_never_equals_target():
    k = key.Key("C")
    target = pitch.Pitch("G5")
    for from_side in (pitch.Pitch("E5"), pitch.Pitch("B5"), pitch.Pitch("G5")):
        result = _approach_tone(target, from_side, k)
        assert result.midi != target.midi


# ── parts_for ─────────────────────────────────────────────────────────────────

def test_parts_for_quarter_into_eighths():
    assert parts_for(1.0, 0.5, 4) == 2


def test_parts_for_half_note_into_eighths():
    assert parts_for(2.0, 0.5, 4) == 4


def test_parts_for_too_short_note_returns_one():
    # A sixteenth note cannot be split into eighths
    assert parts_for(0.25, 0.5, 4) == 1


def test_parts_for_dotted_quarter_into_eighths():
    # 1.5 ÷ 0.5 = 3; each part is 0.5 — a plain (notatable) duration
    assert parts_for(1.5, 0.5, 4) == 3


def test_parts_for_cap_is_respected():
    assert parts_for(4.0, 0.5, 3) <= 3


# ── parse_input: ЗАТАКТ ──────────────────────────────────────────────────────

def test_full_first_measure_is_not_treated_as_pickup(tmp_path):
    # music21's ABC importer numbers the first measure 0 even when it's
    # full — that used to be misread as a pickup, silencing the left hand
    # (and its chords) for the whole first bar.
    p = tmp_path / 'full_bars.abc'
    p.write_text('X:1\nT:t\nM:4/4\nL:1/8\nK:C\n"C"CDEF GABc|"Dm"cBAG FEDC|]',
                 encoding='utf-8')
    ctx = parse_input(str(p))
    assert ctx.pickup_ql == 0.0


def test_parts_for_result_is_always_a_notatable_duration():
    _PLAIN = (4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625)
    _DOTTED = (3.0, 1.5, 0.75, 0.375, 0.1875)
    _ALL = _PLAIN + _DOTTED

    for note_ql in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        for unit_ql in (0.5, 0.25):
            for cap in (2, 4, 6):
                n = parts_for(note_ql, unit_ql, cap)
                part_ql = note_ql / n
                assert any(abs(part_ql - x) < 1e-6 for x in _ALL), (
                    f"parts_for({note_ql}, {unit_ql}, {cap}) = {n};"
                    f" part duration {part_ql} is not a notatable value"
                )
