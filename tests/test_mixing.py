import pytest
from music21 import meter, stream

from hymnarranger import meters
from hymnarranger.mixing import arrange_mixed, phrase_bounds
from hymnarranger.parsing import parse_input

_B44 = ['"G"GABc', '"D"dcBA', '"Em"GABG', '"C"c2B2', '"G"GBdB', '"D"A2G2']
_B34 = ['"C"c2d', '"G"e2d', '"Am"c2B', '"G"G3']

_ABC = {
    '4/4': 'X:1\nT:t\nM:4/4\nL:1/4\nK:G\n' + '|'.join(_B44 * 2) + '|"G"G4|]',
    '3/4': 'X:1\nT:t\nM:3/4\nL:1/4\nK:C\n"C"G|' + '|'.join(_B34 * 3) + '|]',
}


def _melody(tmp_path, kind):
    p = tmp_path / f'{kind.replace("/", "_")}.abc'
    p.write_text(_ABC[kind], encoding='utf-8')
    return str(p)


def test_phrase_bounds_fall_on_bar_starts(tmp_path):
    ctx = parse_input(_melody(tmp_path, '3/4'))
    bar_ql = ctx.ts.barDuration.quarterLength
    bounds = phrase_bounds(ctx, bars_per_phrase=4)
    assert bounds[0] == 0.0 and bounds[-1] == float('inf')
    for b in bounds[1:-1]:
        assert abs((b - ctx.pickup_ql) % bar_ql) < 1e-6


def test_phrase_bounds_four_bars_apart(tmp_path):
    ctx = parse_input(_melody(tmp_path, '4/4'))
    bounds = phrase_bounds(ctx, bars_per_phrase=4)
    bar_ql = ctx.ts.barDuration.quarterLength
    gaps = [b - a for a, b in zip(bounds[:-2], bounds[1:-1])]
    assert gaps and all(abs(g - 4 * bar_ql) < 1e-6 for g in gaps)


@pytest.mark.parametrize('kind', ['4/4', '3/4'])
def test_mixed_score_has_whole_bars_in_both_hands(tmp_path, kind):
    path = _melody(tmp_path, kind)
    ts = meter.TimeSignature(kind)
    presets = meters.presets(ts)
    sc = arrange_mixed(path, [presets['chord_melody'], presets['sixteenths_arp']],
                       verbose=False)
    bar_ql = ts.barDuration.quarterLength
    for part in sc.parts:
        for m in part.getElementsByClass(stream.Measure):
            if m.paddingLeft:        # неповний такт-затакт
                continue
            total = sum(e.duration.quarterLength for e in m.notesAndRests)
            assert abs(total - bar_ql) < 1e-6


def test_mixed_rejects_two_voice_preset(tmp_path):
    path = _melody(tmp_path, '4/4')
    presets = meters.presets(meter.TimeSignature('4/4'))
    with pytest.raises(ValueError):
        arrange_mixed(path, [presets['two_voice_arp']], verbose=False)


# ── POST /mix ─────────────────────────────────────────────────────────────────

def _post_mix(client, kind, query, headers=None):
    return client.post(
        f'/mix?{query}',
        files={'file': (f'{kind.replace("/", "_")}.abc', _ABC[kind].encode('utf-8'))},
        headers=headers or {},
    )


def test_mix_endpoint_returns_phrase_plan(client):
    r = _post_mix(client, '4/4', 'presets=chord_melody,sixteenths_arp&bars_per_phrase=4')
    assert r.status_code == 200, r.text
    body = r.json()
    assert body['musicxml'] and body['abc'] and body['meter'] == '4/4'
    secs = body['sections']
    assert [s['preset'] for s in secs] == ['chord_melody', 'sixteenths_arp',
                                           'chord_melody', 'sixteenths_arp']
    assert secs[0]['from_bar'] == 1 and secs[0]['to_bar'] == 4
    assert secs[1]['from_bar'] == 5 and secs[1]['to_bar'] == 8
    assert secs[-1]['to_bar'] >= secs[-1]['from_bar']


def test_mix_endpoint_rejects_unknown_preset(client):
    r = _post_mix(client, '4/4', 'presets=chord_melody,nope')
    assert r.status_code == 400


def test_mix_endpoint_rejects_two_voice_preset(client):
    r = _post_mix(client, '4/4', 'presets=chord_melody,two_voice_arp')
    assert r.status_code == 400


def test_mix_endpoint_needs_two_presets(client):
    r = _post_mix(client, '4/4', 'presets=chord_melody')
    assert r.status_code == 400


def test_mix_endpoint_requires_presets_param(client):
    r = _post_mix(client, '4/4', 'bars_per_phrase=4')
    assert r.status_code == 422


def test_mix_saves_work_for_logged_in_user(auth_client, make_user):
    from tests.conftest import bearer
    user = make_user()
    r = _post_mix(auth_client, '3/4', 'presets=chord_melody,sixteenths_arp',
                  headers=bearer(user))
    assert r.status_code == 200, r.text
    works = auth_client.get('/works', headers=bearer(user)).json()
    assert works['total'] == 1
    item = works['items'][0]
    assert item['title'] == 'Mix (3/4)'
    assert item['input_params']['kind'] == 'mix'
    assert item['input_params']['presets'] == ['chord_melody', 'sixteenths_arp']
