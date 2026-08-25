import tempfile, os
from collections import Counter
from music21 import converter, harmony
from hymnarranger.abcexport import score_to_abc
from hymnarranger.assembly import arrange
from hymnarranger.suite import arrange_suite
from hymnarranger.meters import presets
from hymnarranger.parsing import parse_input

MELODY = 'X:1\nT:t\nM:3/4\nL:1/8\nK:G\n"G"G4 A2|"D"B4 A2|"G"G6|]'


def _bag(sc):
    """Мультимножина (висоти, тривалість) — інваріант при конвертації."""
    c = Counter()
    for n in sc.recurse().notes:
        if isinstance(n, harmony.ChordSymbol):
            continue
        c[(tuple(sorted(round(p.ps, 2) for p in n.pitches)),
           round(float(n.duration.quarterLength), 4))] += 1
    return c


def _melody_file(tmp_path):
    p = tmp_path / 'm.abc'
    p.write_text(MELODY, encoding='utf-8')
    return str(p)


def test_abc_has_headers(tmp_path):
    ctx = parse_input(_melody_file(tmp_path))
    cfg = list(presets(ctx.ts).values())[0]
    abc = score_to_abc(arrange(_melody_file(tmp_path), cfg, quiet=True))
    for field in ('X:1', 'M:3/4', 'L:1/8', 'K:G', '%%score'):
        assert field in abc
    assert '<music21' not in abc          # регресія на старий баг


def test_roundtrip_preserves_content(tmp_path):
    src = _melody_file(tmp_path)
    score = arrange_suite(src, seed=3, verbose=False)
    abc = score_to_abc(score)
    fd, path = tempfile.mkstemp(suffix='.abc')
    os.close(fd)
    open(path, 'w', encoding='utf-8').write(abc)
    try:
        back = converter.parse(path)
    finally:
        os.unlink(path)
    assert _bag(score) == _bag(back)


def test_accidentals_respect_key(tmp_path):
    p = tmp_path / 'f.abc'
    p.write_text('X:1\nT:t\nM:4/4\nL:1/8\nK:F\n"F"F4 A4|"Bb"_B8|]', encoding='utf-8')
    ctx = parse_input(str(p))
    cfg = list(presets(ctx.ts).values())[0]
    abc = score_to_abc(arrange(str(p), cfg, quiet=True))
    body = abc.split('K:F')[1]
    assert '_B' not in body   # сі-бемоль уже в ключі — знак не дублюється
