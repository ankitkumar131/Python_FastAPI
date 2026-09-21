"""The publisher app: a small FastAPI UI that turns a form into a published GitBook course.

Run it from the repository root:

    python -m publisher.app                     # http://127.0.0.1:8765
    python -m publisher.app --host 0.0.0.0 --token SECRET

The app edits `gitbook-sources.json`, imports the selected Markdown with the existing
importer, regenerates the dashboard and sidebar, then commits and pushes the publication to
the branch GitBook reads. It never force-pushes and never deletes a page that the source
repository does not have.
"""
from __future__ import annotations

import argparse
import os
import secrets
import threading
import time
import uuid
from pathlib import Path

try:  # FastAPI is optional at import time so the module can be inspected offline.
    from fastapi import Body, FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
except ModuleNotFoundError as error:  # pragma: no cover - guidance instead of a traceback
    raise SystemExit('The publisher app needs FastAPI: pip install -r requirements.txt') from error

from publisher import core

STATIC = Path(__file__).resolve().parent / 'static'
app = FastAPI(title='GitBook course publisher', docs_url=None, redoc_url=None)
JOBS: dict[str, dict] = {}
JOB_LOCK = threading.Lock()
PUBLICATION_LOCK = threading.Lock()
TOKEN = ''

# How long a preview/download may take before the UI reports a timeout.
JOB_TIMEOUT = 900


def _require_token(request: Request) -> None:
    if TOKEN and request.headers.get('x-publisher-token', '') != TOKEN:
        raise HTTPException(status_code=401, detail='Missing or wrong publisher token.')


def _job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Unknown job.')
    return job


def _log(job: dict):
    def log(level: str, message: str) -> None:
        if level not in core.LOG_LEVELS:
            level = 'info'
        job['log'].append({'level': level, 'message': message, 'at': time.time()})
    return log


def _start(payload: dict, work) -> dict:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {'id': job_id, 'status': 'running', 'log': [], 'result': None,
                    'error': '', 'started': time.time(), 'finished': None}
    job = JOBS[job_id]
    log = _log(job)

    def run() -> None:
        if not PUBLICATION_LOCK.acquire(blocking=False):
            job['status'] = 'error'
            job['error'] = 'Another publication is already running.'
            log('error', job['error'])
            job['finished'] = time.time()
            return
        try:
            output, result = core.capture(work, payload, log)
            for line in (output or '').splitlines():
                if line.strip():
                    log('info', line.rstrip())
            job['result'] = result
            job['status'] = 'done'
        except core.PublisherError as error:
            job['error'] = str(error)
            log('error', str(error))
            job['status'] = 'error'
        except Exception as error:  # pragma: no cover - defensive: keep the UI usable
            job['error'] = f'{type(error).__name__}: {error}'
            log('error', job['error'])
            job['status'] = 'error'
        finally:
            PUBLICATION_LOCK.release()
            job['finished'] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return job


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return (STATIC / 'index.html').read_text(encoding='utf-8')


@app.get('/api/state')
def state() -> dict:
    config = core.load_config()
    local = config.get('local', {})
    return {
        'site_title': config.get('site_title', 'GitBook library'),
        'local': {'title': local.get('title', ''), 'entry': local.get('entry', '')},
        'courses': core.course_summaries(config),
        'repository': core.repository_state(),
        'token_required': bool(TOKEN),
        'limits': {'chapter_mb': 3, 'markdown_mb': 25, 'archive_mb': 25},
    }


@app.post('/api/preview')
def preview(request: Request, payload: dict = Body(...)) -> JSONResponse:
    """Resolve the source and report what would be imported. Writes nothing."""
    _require_token(request)
    try:
        course = core.course_from_form(payload)
        config = core.load_config()
        result = core.preview_course(course, config)
    except core.PublisherError as error:
        return JSONResponse(status_code=400, content={'error': str(error)})
    return JSONResponse(content={'ok': True, 'preview': result})


@app.post('/api/publish')
def publish(request: Request, payload: dict = Body(...)) -> dict:
    _require_token(request)
    job = _start(payload, core.publish)
    return {'ok': True, 'job': job['id']}


@app.post('/api/remove')
def remove(request: Request, payload: dict = Body(...)) -> dict:
    """Drop a course from the registry, its imported copy, and the generated navigation."""
    _require_token(request)
    course_id = (payload.get('id') or '').strip()

    def work(payload: dict, log) -> dict:
        config = core.load_config()
        match = [course for course in config['imports'] if course['id'] == course_id]
        if not match:
            raise core.PublisherError(f'No configured course with ID {course_id!r}.')
        course = match[0]
        engine = core.engine
        folder = engine.destination(course)
        config['imports'] = [item for item in config['imports'] if item['id'] != course_id]
        if folder.exists():
            for path in sorted(folder.rglob('*'), reverse=True):
                path.unlink() if path.is_file() else path.rmdir()
            folder.rmdir()
            log('info', f'Removed {folder.relative_to(engine.ROOT)}')
        engine.write_generated(config)
        log('step', 'Regenerated the dashboard and the sidebar without that course.')
        core.save_config(config)
        engine.check(config)
        log('done', f'“{course_id}” removed. Press “Publish library” to push the removal.')
        return {'removed': course_id}

    job = _start(payload, work)
    return {'ok': True, 'job': job['id']}


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str) -> dict:
    job = _job(job_id)
    return {'id': job['id'], 'status': job['status'], 'log': job['log'],
            'result': job['result'], 'error': job['error'],
            'seconds': round((job['finished'] or time.time()) - job['started'], 1)}


def main() -> None:
    global TOKEN
    parser = argparse.ArgumentParser(description='GitBook course publisher app')
    parser.add_argument('--host', default=os.environ.get('PUBLISHER_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('PUBLISHER_PORT', '8765')))
    parser.add_argument('--token', default=os.environ.get('PUBLISHER_TOKEN', ''))
    args = parser.parse_args()
    TOKEN = args.token
    if not TOKEN and args.host not in ('127.0.0.1', 'localhost'):
        TOKEN = secrets.token_urlsafe(9)
        print(f'Publishing token (required for preview, publish and remove): {TOKEN}')
    if not TOKEN:
        print('Serving on loopback only; set --token to expose this on a network.')
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
