"""FastAPI backend for HymnArranger."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .assembly import arrange, arrange_multi, save, to_musicxml_string
from .meters import presets, is_compound
from .parsing import parse_input
from .suite import arrange_suite, resolve_suite


class ScoreIn(BaseModel):
    musicxml: str


async def _read_source(
    file: Optional[UploadFile],
    body: Optional[ScoreIn],
) -> Path:
    if file is not None:
        suffix = Path(file.filename).suffix or '.mxl'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            return Path(tmp.name)
    if body is not None:
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as tmp:
            tmp.write(body.musicxml)
            return Path(tmp.name)
    raise HTTPException(422, 'Provide either a file upload or a JSON body with "musicxml" field.')


app = FastAPI(title='HymnArranger API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/analyze')
async def analyze(
    file: Optional[UploadFile] = File(None),
    body: Optional[ScoreIn] = Body(None),
    seed: Optional[int] = Query(None),
):
    path = await _read_source(file, body)
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        suite_names = resolve_suite(ctx.ts, seed=seed)
        measures = round(ctx.total_ql / ctx.ts.barDuration.quarterLength)
        return {
            'meter': ctx.ts.ratioString,
            'meter_family': 'compound' if is_compound(ctx.ts) else 'simple',
            'key': ctx.key.name,
            'sharps': ctx.key.sharps,
            'measures': measures,
            'total_ql': ctx.total_ql,
            'pickup_ql': ctx.pickup_ql,
            'chord_source': ctx.chord_source,
            'chords': [{'offset': off, 'figure': cs.figure} for off, cs in ctx.chords],
            'warnings': ctx.warnings,
            'presets': [
                {'id': k, 'name': v.name, 'tempo': v.tempo or 84, 'mode': v.mode}
                for k, v in ps.items()
            ],
            'suite': [
                {
                    'index': i + 1,
                    'preset': n,
                    'name': ps[n].name,
                    'tempo': ps[n].tempo or 84,
                    'bass': ps[n].lh_pattern,
                }
                for i, n in enumerate(suite_names)
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@app.post('/arrange')
async def arrange_endpoint(
    file: Optional[UploadFile] = File(None),
    body: Optional[ScoreIn] = Body(None),
    preset: Optional[str] = Query(None),
    download: bool = Query(False),
):
    path = await _read_source(file, body)
    stem = Path(file.filename).stem if file else 'arranged'
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        name = preset or next(iter(ps))
        if name not in ps:
            raise HTTPException(400, f'Unknown preset {name!r}. Available: {", ".join(ps)}')
        cfg = ps[name]
        score = arrange(str(path), cfg)

        if download:
            out = tempfile.NamedTemporaryFile(suffix='.mxl', delete=False)
            out.close()
            out_path = Path(out.name)
            save(score, out_path)
            return FileResponse(str(out_path), media_type='application/octet-stream',
                                filename=stem + '_arranged.mxl')

        return {
            'musicxml': to_musicxml_string(score),
            'preset': name,
            'name': cfg.name,
            'tempo': cfg.tempo or 84,
            'meter': ctx.ts.ratioString,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@app.post('/suite')
async def suite_endpoint(
    file: Optional[UploadFile] = File(None),
    body: Optional[ScoreIn] = Body(None),
    seed: Optional[int] = Query(None),
    vary_bass: bool = Query(True),
    download: bool = Query(False),
):
    path = await _read_source(file, body)
    stem = Path(file.filename).stem if file else 'suite'
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        suite_names = resolve_suite(ctx.ts, seed=seed)
        score = arrange_suite(str(path), seed=seed, vary_bass=vary_bass)

        if download:
            out = tempfile.NamedTemporaryFile(suffix='.mxl', delete=False)
            out.close()
            out_path = Path(out.name)
            save(score, out_path)
            return FileResponse(str(out_path), media_type='application/octet-stream',
                                filename=stem + '_suite.mxl')

        return {
            'musicxml': to_musicxml_string(score),
            'meter': ctx.ts.ratioString,
            'meter_family': 'compound' if is_compound(ctx.ts) else 'simple',
            'seed': seed,
            'sections': [
                {
                    'index': i + 1,
                    'preset': n,
                    'name': ps[n].name,
                    'tempo': ps[n].tempo or 84,
                    'bass': ps[n].lh_pattern,
                }
                for i, n in enumerate(suite_names)
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@app.post('/merge')
async def merge_endpoint(
    file: Optional[UploadFile] = File(None),
    body: Optional[ScoreIn] = Body(None),
    download: bool = Query(False),
):
    path = await _read_source(file, body)
    stem = Path(file.filename).stem if file else 'merge'
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        preset_names = list(ps)
        score = arrange_multi(str(path), presets=preset_names, preset_map=ps)

        if download:
            out = tempfile.NamedTemporaryFile(suffix='.mxl', delete=False)
            out.close()
            out_path = Path(out.name)
            save(score, out_path)
            return FileResponse(str(out_path), media_type='application/octet-stream',
                                filename=stem + '_merge.mxl')

        return {
            'musicxml': to_musicxml_string(score),
            'meter': ctx.ts.ratioString,
            'sections': [{'preset': k, 'name': v.name} for k, v in ps.items()],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@app.post('/midi')
async def midi(
    file: Optional[UploadFile] = File(None),
    body: Optional[ScoreIn] = Body(None),
    seed: Optional[int] = Query(None),
    preset: Optional[str] = Query(None),
):
    """
    Та сама музика у форматі MIDI.

    Потрібен для надійного відтворення в браузері: MIDI несе
    program change 21 (GM Accordion), тож будь-який програвач із
    GM-банком дасть саме баян.
    """
    path = await _read_source(file, body)

    out = tempfile.NamedTemporaryFile(suffix='.mid', delete=False)
    out.close()
    out_path = Path(out.name)

    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        name = preset or next(iter(ps))
        if name not in ps:
            raise HTTPException(400, f'Unknown preset {name!r}. Available: {", ".join(ps)}')
        score = arrange(str(path), ps[name])

        score.write('midi', fp=str(out_path))

        stem = Path(file.filename).stem if file else 'arranged'
        return FileResponse(str(out_path), media_type='audio/midi',
                            filename=stem + '.mid')
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)
