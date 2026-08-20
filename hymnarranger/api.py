"""HTTP-інтерфейс до аранжувальника.

Розрахований на фронтенд із вбудованим нотним редактором: той віддає
MusicXML рядком (`embed.getMusicXML()`), сервер повертає теж рядок, який
одразу заходить у `embed.loadMusicXML()`. Тому типова відповідь — JSON
із полем `musicxml`, а не файл на завантаження; файл віддається лише
коли клієнт просить `?download=true`.

Запуск:
    uvicorn hymnarranger.api:app --reload
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field

from . import meters
from .parsing import parse_input
from .assembly import (arrange, arrange_multi, save, to_musicxml_string,
                       midi_bytes)
from .suite import arrange_suite, plan_suite
from . import styles
from hymnarranger.auth.routes import router as auth_router


MAX_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIX = ('.mxl', '.musicxml', '.xml')

app = FastAPI(
    title='HymnArranger API',
    version='2.0',
    description='Генерує баянне аранжування з мелодії та акордових символів.',
)

# Фронтенд живе на іншому порту, тож без CORS браузер заблокує запити.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)
app.include_router(auth_router)


# =================================================================
#  Схеми
# =================================================================

class ScoreIn(BaseModel):
    musicxml: str = Field(..., description='Вміст MusicXML рядком')


class PresetOut(BaseModel):
    id: str
    name: str
    tempo: int
    mode: str


class ChordOut(BaseModel):
    offset: float
    figure: str


class AnalyzeOut(BaseModel):
    meter: str
    meter_family: str
    key: str
    sharps: int
    measures: int
    total_ql: float
    pickup_ql: float
    chord_source: str
    chords: List[ChordOut]
    warnings: List[str]
    presets: List[PresetOut]
    suite: List[dict]


class ArrangeOut(BaseModel):
    musicxml: str
    preset: str
    name: str
    tempo: int
    meter: str


class SuiteOut(BaseModel):
    musicxml: str
    meter: str
    meter_family: str
    seed: Optional[int]
    sections: List[dict]


# =================================================================
#  Допоміжне
# =================================================================

async def _read_source(request: Request) -> str:
    """
    Приймає партитуру в будь-якому з трьох виглядів:
      * multipart/form-data з полем "file"  — завантаження .mxl / .musicxml
      * application/json  {"musicxml": "..."} — те, що віддає нотний редактор
      * сирий XML у тілі із Content-Type application/xml

    Читання зроблено на рівні Request, а не через File()/Body(): якщо в
    одному ендпоінті оголосити і те, і те, FastAPI завжди чекає multipart
    і JSON просто не розбирає.

    Повертає шлях до тимчасового файлу — music21 читає з диска, а .mxl
    взагалі є zip-архівом, тож у пам'яті його не розібрати.
    """
    ctype = (request.headers.get('content-type') or '').lower()
    data, suffix = None, '.musicxml'

    if ctype.startswith('multipart/form-data'):
        form = await request.form()
        up = form.get('file')
        if up is None or not hasattr(up, 'read'):
            raise HTTPException(400, 'У формі немає поля "file"')
        ext = os.path.splitext(getattr(up, 'filename', '') or '')[1].lower()
        if ext and ext not in ALLOWED_SUFFIX:
            raise HTTPException(400, f'Непідтримуване розширення {ext}. '
                                     f'Очікується {", ".join(ALLOWED_SUFFIX)}')
        data = await up.read()
        suffix = ext or '.musicxml'
    else:
        raw = await request.body()
        if raw and ctype.startswith('application/json'):
            import json
            try:
                payload = json.loads(raw.decode('utf-8'))
            except Exception:
                raise HTTPException(400, 'Тіло не є коректним JSON')
            text = (payload or {}).get('musicxml')
            if not text or not str(text).strip():
                raise HTTPException(400, 'У JSON немає непорожнього поля "musicxml"')
            data = str(text).encode('utf-8')
        elif raw:
            data = raw

    if not data:
        raise HTTPException(400, 'Потрібен файл (form-data "file"), '
                                 'поле "musicxml" у JSON або сирий XML у тілі')
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f'Файл більший за {MAX_BYTES // 1024 // 1024} МБ')

    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'wb') as fh:
        fh.write(data)
    return path


def _context(path: str):
    try:
        return parse_input(path)
    except Exception as exc:
        raise HTTPException(422, f'Не вдалося прочитати партитуру: {exc}')


def _download(score, filename: str) -> StreamingResponse:
    fd, tmp = tempfile.mkstemp(prefix=filename[:-4] + '_', suffix='.mxl')
    os.close(fd)
    try:
        save(score, tmp)
        payload = open(tmp, 'rb').read()
    finally:
        os.unlink(tmp)
    return StreamingResponse(
        io.BytesIO(payload),
        media_type='application/vnd.recordare.musicxml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _download_name(stem: str) -> str:
    keep = ''.join(ch for ch in stem if ch.isalnum() or ch in '-_')
    return (keep or 'score') + '.mxl'


# =================================================================
#  Ендпоінти
# =================================================================

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


@app.get('/', response_class=HTMLResponse)
def demo_page():
    """Демо-сторінка: завантажити мелодію, побачити ноти і почути баян."""
    path = os.path.join(STATIC_DIR, 'demo.html')
    if not os.path.exists(path):
        return HTMLResponse('<h1>HymnArranger API</h1>'
                            '<p>Документація: <a href="/docs">/docs</a></p>')
    return HTMLResponse(open(path, encoding='utf-8').read())


@app.get('/health')
def health():
    return {'status': 'ok', 'version': app.version}


@app.post('/analyze', response_model=AnalyzeOut)
async def analyze(request: Request, seed: Optional[int] = Query(None)):
    """
    Що система побачила у вхідному файлі і що збирається з ним зробити.
    Викликати ПЕРЕД генерацією: тут повертаються попередження на кшталт
    "акордів не знайдено", і клієнт може виправити ноти, не чекаючи
    порожньої лівої руки у відповіді.
    """
    path = await _read_source(request)
    try:
        ctx = _context(path)
        ts = ctx.ts
        presets = meters.presets(ts)
        sections = plan_suite(ts, seed=seed)
        return AnalyzeOut(
            meter=ts.ratioString,
            meter_family='compound' if meters.is_compound(ts) else 'simple',
            key=str(ctx.key),
            sharps=ctx.key.sharps,
            measures=int(round((ctx.total_ql - ctx.pickup_ql)
                               / ts.barDuration.quarterLength)),
            total_ql=ctx.total_ql,
            pickup_ql=ctx.pickup_ql,
            chord_source=ctx.chord_source,
            chords=[ChordOut(offset=o, figure=c.figure or '') for o, c in ctx.chords],
            warnings=ctx.warnings,
            presets=[PresetOut(id=k, name=c.name, tempo=c.tempo or 84, mode=c.mode)
                     for k, c in presets.items()],
            suite=[{'index': i, 'preset': preset, 'name': cfg.name,
                    'tempo': cfg.tempo, 'bass': cfg.lh_pattern}
                   for i, (preset, cfg) in enumerate(sections)],
        )
    finally:
        os.unlink(path)


@app.post('/arrange')
async def arrange_one(request: Request,
                      preset: str = Query('theme'),
                      download: bool = Query(False)):
    """Один варіант аранжування."""
    path = await _read_source(request)
    try:
        ctx = _context(path)
        presets = meters.presets(ctx.ts)
        if preset not in presets:
            raise HTTPException(
                404, f'Пресет {preset!r} недоступний для розміру '
                     f'{ctx.ts.ratioString}. Доступні: {", ".join(presets)}')
        cfg = presets[preset]
        score = arrange(path, cfg, quiet=True)
        if download:
            return _download(score, f'{preset}.mxl')
        return ArrangeOut(musicxml=to_musicxml_string(score), preset=preset,
                          name=cfg.name, tempo=cfg.tempo or 84,
                          meter=ctx.ts.ratioString)
    finally:
        os.unlink(path)


@app.post('/suite')
async def suite(request: Request,
                seed: Optional[int] = Query(None),
                vary_bass: bool = Query(True),
                download: bool = Query(False)):
    """Готова п'єса: тема + варіації в одній партитурі."""
    path = await _read_source(request)
    try:
        ctx = _context(path)
        sections = plan_suite(ctx.ts, seed=seed, vary_bass=vary_bass)
        score = arrange_suite(path, seed=seed, vary_bass=vary_bass, verbose=False)
        if download:
            return _download(score, 'suite.mxl')
        return SuiteOut(
            musicxml=to_musicxml_string(score),
            meter=ctx.ts.ratioString,
            meter_family='compound' if meters.is_compound(ctx.ts) else 'simple',
            seed=seed,
            sections=[{'index': i, 'preset': preset, 'name': cfg.name,
                       'tempo': cfg.tempo, 'bass': cfg.lh_pattern}
                      for i, (preset, cfg) in enumerate(sections)],
        )
    finally:
        os.unlink(path)


@app.post('/style')
async def style_arrange(request: Request,
                        style: str = Query('sakala'),
                        strophes: int = Query(5, ge=1, le=5),
                        coda: bool = Query(True),
                        download: bool = Query(False)):
    """
    Стильова обробка: строфи різної фактури, хроматичні зв'язки, кода.

    На відміну від /suite, де кожен розділ незалежний, тут форма
    цілісна — регістр наростає від строфи до строфи, а зв'язки
    щоразу повертають до домінанти.
    """
    path = await _read_source(request)
    try:
        try:
            mod = styles.get(style)
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        ctx = _context(path)
        score = mod.arrange_style(path, n_strophes=strophes,
                                  with_coda=coda, verbose=False)
        if download:
            return _download(score, f'{style}.mxl')
        return {'musicxml': to_musicxml_string(score),
                'style': style,
                'meter': ctx.ts.ratioString,
                'key': str(ctx.key),
                'sections': mod.describe(strophes, coda)}
    finally:
        os.unlink(path)


@app.post('/midi')
async def midi(request: Request,
               seed: Optional[int] = Query(None),
               preset: Optional[str] = Query(None)):
    """
    Та сама музика у форматі MIDI.

    Потрібен для надійного відтворення в браузері: MIDI несе
    program change 21 (GM Accordion), тож будь-який програвач із
    GM-банком дасть саме баян. У MusicXML звук залежить від того,
    як конкретний переглядач розпізнає <instrument-sound>.
    """
    path = await _read_source(request)
    try:
        ctx = _context(path)
        if preset and preset.startswith('style:'):
            try:
                mod = styles.get(preset.split(':', 1)[1])
            except KeyError as exc:
                raise HTTPException(404, str(exc))
            score = mod.arrange_style(path, verbose=False)
        elif preset:
            presets = meters.presets(ctx.ts)
            if preset not in presets:
                raise HTTPException(404, f'Пресет {preset!r} недоступний для '
                                         f'розміру {ctx.ts.ratioString}')
            score = arrange(path, presets[preset], quiet=True)
        else:
            score = arrange_suite(path, seed=seed, verbose=False)
        return StreamingResponse(
            io.BytesIO(midi_bytes(score)),
            media_type='audio/midi',
            headers={'Content-Disposition': 'inline; filename="arrangement.mid"'},
        )
    finally:
        os.unlink(path)


@app.post('/merge')
async def merge(request: Request, download: bool = Query(False)):
    """Усі доступні пресети підряд — для порівняння на слух."""
    path = await _read_source(request)
    try:
        ctx = _context(path)
        presets = meters.presets(ctx.ts)
        score = arrange_multi(path, presets=list(presets), preset_map=presets)
        if download:
            return _download(score, 'merge.mxl')
        return {'musicxml': to_musicxml_string(score),
                'meter': ctx.ts.ratioString,
                'sections': [{'preset': k, 'name': c.name} for k, c in presets.items()]}
    finally:
        os.unlink(path)