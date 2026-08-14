"""FastAPI backend for HymnArranger."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .assembly import arrange, arrange_multi, save
from .meters import presets, is_compound
from .parsing import parse_input
from .suite import arrange_suite


class ScoreIn(BaseModel):
    xml: str  # MusicXML content as a string


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
            tmp.write(body.xml)
            return Path(tmp.name)
    raise HTTPException(422, 'Provide either a file upload or a JSON body with "xml" field.')

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


@app.post('/presets')
async def list_presets(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        ctx = parse_input(str(tmp_path))
        ps = presets(ctx.ts)
        kind = 'compound' if is_compound(ctx.ts) else 'simple'
        return {'meter': ctx.ts.ratioString, 'kind': kind,
                'presets': [{'id': k, 'name': v.name} for k, v in ps.items()]}
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post('/arrange')
async def arrange_file(
    file: UploadFile = File(...),
    preset: str = Query(default=None),
    mode: str = Query(default='single'),  # 'single' | 'all' | 'suite'
):
    suffix = Path(file.filename).suffix or '.mxl'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    out = tempfile.NamedTemporaryFile(suffix='.mxl', delete=False)
    out.close()
    out_path = Path(out.name)

    try:
        ctx = parse_input(str(tmp_path))
        ps = presets(ctx.ts)

        if mode == 'suite':
            score = arrange_suite(str(tmp_path))
        elif mode == 'all':
            score = arrange_multi(str(tmp_path), presets=list(ps), preset_map=ps)
        else:
            name = preset or next(iter(ps))
            if name not in ps:
                raise HTTPException(400, f'Unknown preset {name!r}. Available: {", ".join(ps)}')
            score = arrange(str(tmp_path), ps[name])

        save(score, out_path)
        return FileResponse(str(out_path), media_type='application/octet-stream',
                            filename=Path(file.filename).stem + '_arranged.mxl')
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post('/midi')
async def midi(file: Optional[UploadFile] = File(None),
               body: Optional[ScoreIn] = Body(None),
               seed: Optional[int] = Query(None),
               preset: Optional[str] = Query(None)):
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

        import music21
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
