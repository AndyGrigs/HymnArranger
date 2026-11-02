from dataclasses import replace

from hymnarranger import arrange, meters, parse_input
from hymnarranger.colors import add_neapolitan, neapolitan_candidates
from hymnarranger.mixing import arrange_mixed

SRC = 'input/test_new.mxl'


def _bar_pitches(score, hand, bar):
    return {p.name for el in score.parts[hand].measure(bar).recurse().notes
            for p in el.pitches}


def test_neapolitan_replaces_one_chord_and_sets_local_key():
    ctx = parse_input(SRC)
    out = add_neapolitan(ctx, seed=1)
    assert len(neapolitan_candidates(ctx)) == 1
    assert out is not ctx and not ctx.local_keys          # вихідний контекст не змінено
    assert out.chord_at(12.0).figure == 'D-/F'
    assert out.key_at(13.0).tonic.name == 'D-' and out.key_at(20.0) == ctx.key


def test_arrange_with_neapolitan_puts_third_in_bass():
    p = meters.presets(parse_input(SRC).ts)['eighths_nb']
    sc = arrange(SRC, replace(p, neapolitan=True, neapolitan_seed=1), quiet=True)
    assert _bar_pitches(sc, 1, 4) == {'A-', 'D-', 'F'}
    assert not _bar_pitches(sc, 0, 4) & {'E', 'G', 'B'}   # жодної ноти поза D-мажором


def test_neapolitan_off_leaves_bar_unchanged():
    p = meters.presets(parse_input(SRC).ts)['eighths_nb']
    plain = arrange(SRC, p, quiet=True)
    assert 'D-' not in _bar_pitches(plain, 1, 4)


def test_mix_applies_neapolitan_to_all_phrases():
    P = meters.presets(parse_input(SRC).ts)
    cfgs = [replace(P['eighths_nb'], neapolitan=True, neapolitan_seed=1), P['eighths_ct']]
    sc = arrange_mixed(SRC, cfgs, bars_per_phrase=4, verbose=False)
    assert 'D-' in _bar_pitches(sc, 1, 4)
