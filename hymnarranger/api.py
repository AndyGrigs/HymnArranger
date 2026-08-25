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

import asyncio
import functools
import io
import logging
import os
import tempfile
from typing import Optional, List

logger = logging.getLogger(__name__)

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import meters
from .parsing import parse_input
from .assembly import (arrange, arrange_multi, save, to_musicxml_string,
                       to_abc_string, midi_bytes)
from .suite import arrange_suite, plan_suite
from . import styles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from hymnarranger.auth.limiter import limiter
from hymnarranger.auth.routes import router as auth_router
from sqlalchemy.orm import Session

from hymnarranger.auth.dependencies import get_current_user_optional
from hymnarranger.db.models import User
from hymnarranger.db.session import get_db
from hymnarranger.db.works import save_generated_work
from hymnarranger.works.routes import router as works_router


ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]

if os.getenv('ALLOWED_HOSTS') is None:
    logger.warning(
        'ALLOWED_HOSTS не задано — діє дефолт %s. '
        'У проді це поверне 400 на всі запити.', ALLOWED_HOSTS
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        if request.url.scheme == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response


MAX_BYTES = 5 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # zip-bomb: ліміт на розпакований розмір
MAX_MEASURES = 200          # понад 200 тактів → відмовляємо до аранжування
ARRANGE_TIMEOUT = 45.0      # секунди на одну операцію аранжування
ALLOWED_SUFFIX = ('.mxl', '.musicxml', '.xml', '.abc')


def _validate_file(path: str) -> None:
    """Захист від XML-бомб і zip-бомб перед передачею в music21.

    .mxl — це ZIP: перевіряємо сумарний розпакований розмір і кожен
    XML-файл усередині через defusedxml. Для чистого .musicxml/.xml
    перевіряємо сам файл через defusedxml.

    Ловимо лише security-специфічні виключення defusedxml (entity expansion,
    DTD, external references). Звичайний ParseError пропускаємо — music21
    сам підніме зрозумілу помилку і _context поверне 422.
    """
    import zipfile
    from defusedxml import DefusedXmlException, DTDForbidden, EntitiesForbidden
    import defusedxml.ElementTree as dET

    _SECURITY_ERRORS = (DefusedXmlException, DTDForbidden, EntitiesForbidden)

    def _check_xml(fileobj) -> None:
        try:
            dET.parse(fileobj)
        except _SECURITY_ERRORS as exc:
            raise HTTPException(400, f'Небезпечний XML: {exc}')
        except Exception:
            pass  # ParseError або не-XML — залишаємо music21

    if path.lower().endswith('.mxl'):
        if not zipfile.is_zipfile(path):
            raise HTTPException(400, 'Файл .mxl не є коректним ZIP-архівом')
        with zipfile.ZipFile(path, 'r') as zf:
            total = sum(i.file_size for i in zf.infolist())
            if total > MAX_UNCOMPRESSED_BYTES:
                raise HTTPException(
                    413,
                    f'Розпакований вміст перевищує '
                    f'{MAX_UNCOMPRESSED_BYTES // 1024 // 1024} МБ (zip-бомба?)',
                )
            for info in zf.infolist():
                if info.filename.endswith(('.xml', '.musicxml')):
                    with zf.open(info) as f:
                        _check_xml(f)
    else:
        _check_xml(path)


def _check_measures(ctx) -> None:
    n = int(round((ctx.total_ql - ctx.pickup_ql) / ctx.ts.barDuration.quarterLength))
    if n > MAX_MEASURES:
        raise HTTPException(
            400,
            f'Партитура містить {n} тактів — максимум {MAX_MEASURES}. '
            'Скоротіть або розбийте на частини.',
        )


async def _run_sync(fn, *, timeout: float = ARRANGE_TIMEOUT):
    """Запускає синхронну CPU-важку функцію в thread pool з таймаутом."""
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, fn),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            504,
            f'Аранжування перевищило ліміт часу ({int(timeout)} с)',
        )


app = FastAPI(
    title='HymnArranger API',
    version='2.0',
    description='Генерує баянне аранжування з мелодії та акордових символів.',
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Фронтенд живе на іншому порту, тож без CORS браузер заблокує запити.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.include_router(auth_router)
app.include_router(works_router)

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
    abc: Optional[str] = None
    preset: str
    name: str
    tempo: int
    meter: str


class SuiteOut(BaseModel):
    musicxml: str
    abc: Optional[str] = None
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
    cl_header = request.headers.get('content-length')
    if cl_header is not None:
        try:
            if int(cl_header) > MAX_BYTES:
                raise HTTPException(413, f'Файл більший за {MAX_BYTES // 1024 // 1024} МБ')
        except ValueError:
            pass  # некоректний заголовок — перевіримо після читання

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
                raise HTTPException(422, 'У JSON немає непорожнього поля "musicxml"')
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
    _validate_file(path)
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
        media_type='application/octet-stream',
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
    return {'status': 'ok'}


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
                      download: bool = Query(False),
                      db: Session = Depends(get_db),
                      current_user: Optional[User] = Depends(get_current_user_optional)):
    """Один варіант аранжування."""
    path = await _read_source(request)
    try:
        ctx = _context(path)
        presets = meters.presets(ctx.ts)
        if preset not in presets:
            raise HTTPException(
                400, f'Пресет {preset!r} недоступний для розміру '
                     f'{ctx.ts.ratioString}. Доступні: {", ".join(presets)}')
        cfg = presets[preset]
        _check_measures(ctx)
        score = await _run_sync(functools.partial(arrange, path, cfg, quiet=True))
        musicxml_str = to_musicxml_string(score)

        if current_user is not None:
            _source_abc: Optional[str] = None
            try:
                import music21 as _m21
                _source_abc = to_abc_string(_m21.converter.parse(path))
            except Exception as exc:
                logger.warning('ABC export failed (source, arrange): %s', exc)
            save_generated_work(
                db, current_user,
                title=f'{cfg.name} ({preset})',
                input_params={'preset': preset, 'meter': ctx.ts.ratioString},
                musicxml_content=musicxml_str,
                source_abc=_source_abc,
            )

        if download:
            return _download(score, f'{preset}.mxl')
        try:
            abc_str: Optional[str] = to_abc_string(score)
        except Exception as exc:
            logger.warning('ABC export failed (output, arrange): %s', exc)
            abc_str = None
        return ArrangeOut(musicxml=musicxml_str, abc=abc_str, preset=preset,
                          name=cfg.name, tempo=cfg.tempo or 84,
                          meter=ctx.ts.ratioString)
    finally:
        os.unlink(path)


@app.post('/suite')
async def suite(request: Request,
                seed: Optional[int] = Query(None),
                vary_bass: bool = Query(True),
                download: bool = Query(False),
                db: Session = Depends(get_db),
                current_user: Optional[User] = Depends(get_current_user_optional)):
    """Готова п'єса: тема + варіації в одній партитурі."""
    path = await _read_source(request)
    try:
        ctx = _context(path)
        sections = plan_suite(ctx.ts, seed=seed, vary_bass=vary_bass)
        _check_measures(ctx)
        score = await _run_sync(
            functools.partial(arrange_suite, path, seed=seed, vary_bass=vary_bass, verbose=False)
        )
        musicxml_str = to_musicxml_string(score)

        if current_user is not None:
            _source_abc_s: Optional[str] = None
            try:
                import music21 as _m21
                _source_abc_s = to_abc_string(_m21.converter.parse(path))
            except Exception as exc:
                logger.warning('ABC export failed (source, suite): %s', exc)
            save_generated_work(
                db, current_user,
                title=f'Suite ({ctx.ts.ratioString})',
                input_params={'seed': seed, 'vary_bass': vary_bass, 'meter': ctx.ts.ratioString},
                musicxml_content=musicxml_str,
                source_abc=_source_abc_s,
            )

        if download:
            return _download(score, 'suite.mxl')
        try:
            abc_str_s: Optional[str] = to_abc_string(score)
        except Exception as exc:
            logger.warning('ABC export failed (output, suite): %s', exc)
            abc_str_s = None
        return SuiteOut(
            musicxml=musicxml_str,
            abc=abc_str_s,
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
        _check_measures(ctx)
        score = await _run_sync(
            functools.partial(mod.arrange_style, path, n_strophes=strophes,
                              with_coda=coda, verbose=False)
        )
        if download:
            return _download(score, f'{style}.mxl')
        musicxml_s = to_musicxml_string(score)
        try:
            abc_s: Optional[str] = to_abc_string(score)
        except Exception as exc:
            logger.warning('ABC export failed (output, style): %s', exc)
            abc_s = None
        return {'musicxml': musicxml_s, 'abc': abc_s,
                'style': style,
                'meter': ctx.ts.ratioString,
                'key': str(ctx.key),
                'sections': mod.describe(strophes, coda)}
    finally:
        os.unlink(path)


@app.post('/midi')
async def midi(request: Request,
               raw: bool = Query(False),
               seed: Optional[int] = Query(None),
               preset: Optional[str] = Query(None)):
    """
    Та сама музика у форматі MIDI.

    ?raw=true — конвертує переданий MusicXML напряму, без аранжування.
    Використовується коли клієнт вже має готову партитуру в пам'яті.
    Без raw= — аранжує мелодію (suite або обраний preset).
    """
    import music21
    path = await _read_source(request)
    try:
        if raw:
            _validate_file(path)
            score = music21.converter.parse(path)
        elif preset and preset.startswith('style:'):
            try:
                mod = styles.get(preset.split(':', 1)[1])
            except KeyError as exc:
                raise HTTPException(404, str(exc))
            ctx = _context(path)
            _check_measures(ctx)
            score = await _run_sync(
                functools.partial(mod.arrange_style, path, verbose=False)
            )
        elif preset:
            ctx = _context(path)
            presets = meters.presets(ctx.ts)
            if preset not in presets:
                raise HTTPException(404, f'Пресет {preset!r} недоступний для '
                                         f'розміру {ctx.ts.ratioString}')
            _check_measures(ctx)
            score = await _run_sync(
                functools.partial(arrange, path, presets[preset], quiet=True)
            )
        else:
            ctx = _context(path)
            _check_measures(ctx)
            score = await _run_sync(
                functools.partial(arrange_suite, path, seed=seed, verbose=False)
            )
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
        _check_measures(ctx)
        score = await _run_sync(
            functools.partial(arrange_multi, path, presets=list(presets), preset_map=presets)
        )
        if download:
            return _download(score, 'merge.mxl')
        musicxml_m = to_musicxml_string(score)
        try:
            abc_m: Optional[str] = to_abc_string(score)
        except Exception as exc:
            logger.warning('ABC export failed (output, merge): %s', exc)
            abc_m = None
        return {'musicxml': musicxml_m, 'abc': abc_m,
                'meter': ctx.ts.ratioString,
                'sections': [{'preset': k, 'name': c.name} for k, c in presets.items()]}
    finally:
        os.unlink(path)


@app.post('/compress')
async def compress_mxl(request: Request):
    """Стискає MusicXML у формат .mxl (ZIP) без повторного аранжування."""
    import shutil
    import music21
    path = await _read_source(request)
    try:
        _validate_file(path)
        score = music21.converter.parse(path)
        tmpdir = tempfile.mkdtemp()
        try:
            tmp = os.path.join(tmpdir, 'score.mxl')
            save(score, tmp)
            payload = open(tmp, 'rb').read()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return StreamingResponse(
            io.BytesIO(payload),
            media_type='application/octet-stream',
            headers={'Content-Disposition': 'attachment; filename="score.mxl"'},
        )
    finally:
        os.unlink(path)


@app.post('/convert/abc')
async def convert_to_abc(request: Request):
    """Конвертує будь-який підтримуваний формат (MusicXML, .mxl, .abc) у ABC-нотацію."""
    import music21
    path = await _read_source(request)
    try:
        _validate_file(path)
        sc = await _run_sync(lambda: music21.converter.parse(path), timeout=15.0)
        return {'abc': to_abc_string(sc)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f'Не вдалося конвертувати: {exc}')
    finally:
        os.unlink(path)