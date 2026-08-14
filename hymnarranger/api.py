"""FastAPI backend for HymnArranger."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .assembly import arrange, arrange_multi, save, to_musicxml_string
from .meters import presets, is_compound
from .parsing import parse_input
from .suite import plan_suite


class ScoreIn(BaseModel):
    """Лишено для документації: тіло запиту у JSON-режимі."""
    musicxml: str


async def _read_source(request: Request) -> Tuple[Path, Optional[str]]:
    """
    Приймає ноти двома способами й повертає (шлях до тимчасового файлу, ім'я файлу).

    ВАЖЛИВО: розбір іде вручну через Request, а не через File(...)/Body(...)
    у сигнатурі. Якщо в одному ендпоінті оголосити і File, і Body-модель,
    FastAPI вважає весь запит multipart/form-data — і будь-який
    application/json тоді валиться в 422, бо Body ніколи не заповниться.
    Саме через це раніше не працював вбудований нотний редактор.
    """
    ctype = (request.headers.get('content-type') or '').lower()

    # --- JSON: {"musicxml": "<score-partwise ...>"} ---
    if ctype.startswith('application/json'):
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(422, f'Тіло запиту не є коректним JSON: {exc}') from exc
        if not isinstance(payload, dict):
            raise HTTPException(422, 'Очікується JSON-обʼєкт із полем "musicxml".')
        xml = payload.get('musicxml')
        if not isinstance(xml, str) or not xml.strip():
            raise HTTPException(422, 'Поле "musicxml" відсутнє або порожнє.')
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False,
                                         mode='w', encoding='utf-8') as tmp:
            tmp.write(xml)
            return Path(tmp.name), None

    # --- multipart/form-data з полем "file" ---
    if ctype.startswith('multipart/form-data'):
        form = await request.form()
        upload = form.get('file')
        if upload is None or not hasattr(upload, 'read'):
            raise HTTPException(422, 'У формі немає файлу в полі "file".')
        filename = getattr(upload, 'filename', None) or 'melody.mxl'
        suffix = Path(filename).suffix or '.mxl'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await upload.read())
            return Path(tmp.name), filename

    raise HTTPException(
        422,
        'Надішли або multipart-файл у полі "file", '
        'або JSON-тіло з полем "musicxml".',
    )


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
async def analyze(request: Request, seed: Optional[int] = Query(None)):
    path, _ = await _read_source(request)
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        steps = plan_suite(ctx.ts, seed=seed)
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
                    'name': cfg.name,
                    'tempo': cfg.tempo or 84,
                    'bass': cfg.lh_pattern,
                }
                for i, (n, cfg) in enumerate(steps)
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
    request: Request,
    preset: Optional[str] = Query(None),
    download: bool = Query(False),
):
    path, filename = await _read_source(request)
    stem = Path(filename).stem if filename else 'arranged'
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
    request: Request,
    seed: Optional[int] = Query(None),
    vary_bass: bool = Query(True),
    download: bool = Query(False),
):
    path, filename = await _read_source(request)
    stem = Path(filename).stem if filename else 'suite'
    try:
        ctx = parse_input(str(path))

        # Один розрахунок плану — і підписи розділів, і сама музика.
        # Раніше це були два незалежні виклики, тож при seed=None
        # список у відповіді не збігався з нотами.
        steps = plan_suite(ctx.ts, seed=seed, vary_bass=vary_bass)
        score = arrange_multi(str(path), cfgs=[cfg for _, cfg in steps])

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
                    'name': cfg.name,
                    'tempo': cfg.tempo or 84,
                    'bass': cfg.lh_pattern,
                }
                for i, (n, cfg) in enumerate(steps)
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)


@app.post('/merge')
async def merge_endpoint(request: Request, download: bool = Query(False)):
    path, filename = await _read_source(request)
    stem = Path(filename).stem if filename else 'merge'
    try:
        ctx = parse_input(str(path))
        ps = presets(ctx.ts)
        score = arrange_multi(str(path), presets=list(ps), preset_map=ps)

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
    request: Request,
    seed: Optional[int] = Query(None),
    preset: Optional[str] = Query(None),
):
    """
    Та сама музика у форматі MIDI.

    Потрібен для надійного відтворення в браузері: MIDI несе
    program change 21 (GM Accordion), тож будь-який програвач із
    GM-банком дасть саме баян.
    """
    path, filename = await _read_source(request)
    stem = Path(filename).stem if filename else 'arranged'

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

        return FileResponse(str(out_path), media_type='audio/midi',
                            filename=stem + '.mid')
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)