#!/usr/bin/env python3

from time import time
from pathlib import Path
from threading import Lock
from hashlib import sha256
from re import sub as regex_replace
from re import match as regex_match

from flask import Flask, request, Response, json
from waitress import serve
from oxl_utils.ps import process

# to generate: sha256(b'<ADD-TOKEN-HERE>').hexdigest()
TOKEN_HASH_RW = '39097d9b8a14ebc33e98bacaf6bbcc26ae01f995d69aeba0a77fa55298bae853'
TOKEN_HASH_RO = '63e34ec7d0aabaea017f7e0114268d452df41f20f8a92d86f3f4d8438149eac6'  # read-only access
JOB_CONTAINS = 'test'
JOB_PREFIX = ''
LOGS_STRIP_REGEX = []
LOGS_SKIP_REGEX = []

app = Flask('ci-api')
JOB_REGEX = r'[^a-zA-Z0-9_\-]'
PATH_TAIL_CACHE = Path(f'/tmp/ci-api-{int(time())}')
SCTL_FLAGS = '--no-pager --full'
JCTL_FLAGS = f'--no-hostname -q {SCTL_FLAGS}'

tail_lock = Lock()


def _response_json(code: int, data: dict) -> Response:
    return app.response_class(
        response=json.dumps(data, indent=2),
        status=code,
        mimetype='application/json'
    )


def _is_permitted(write: bool) -> bool:
    if 'token' not in request.args:
        return False

    sh = sha256(request.args['token'].encode('utf-8')).hexdigest()
    if write:
        return sh == TOKEN_HASH_RW

    return sh in [TOKEN_HASH_RW, TOKEN_HASH_RO]


def _validate_job(job: str) -> (str, bool):
    job = regex_replace(JOB_REGEX, '', job)

    if not job.startswith(JOB_PREFIX) or job.find(JOB_CONTAINS) == -1:
        return job, False

    job += '.service'

    if process(cmd=f'systemctl list-unit-files {job} {SCTL_FLAGS}', cwd='/tmp')['rc'] != 0:
        return job, False

    return job, True


def _get_job_state(job: str) -> str:
    return process(
        cmd=f"systemctl status {job} {SCTL_FLAGS} | grep Active | cut -d ' ' -f7",
        shell=True,
        cwd='/tmp',
    )['stdout'].strip()


def _get_last_job_exec_id(job: str, force: bool = False) -> str:
    exec_id = process(
        cmd=f"systemctl show --value -p InvocationID {job}",
        cwd='/tmp',
    )['stdout']
    if exec_id == '' and not force:
        return ''

    return f"_SYSTEMD_INVOCATION_ID={exec_id}"


def _get_job_logs(cmd: str) -> list[str]:
    logs = process(cmd=cmd, cwd='/tmp')['stdout']
    if logs is None:
        return []

    return logs.split('\n')


def _clean_logs(logs: list[str]) -> list[str]:
    if len(LOGS_STRIP_REGEX) == 0:
        return logs

    logs_cleaned = []

    for l in logs:
        o = False
        for r in LOGS_SKIP_REGEX:
            if regex_match(r, l) is not None:
                o = True
                break

        if o:
            continue

        s = l

        for r in LOGS_STRIP_REGEX:
            s = regex_replace(r, '', s)

        logs_cleaned.append(s)

    return logs_cleaned


@app.route('/api/job/<job>', methods=['POST'])
def api_start_job(job: str) -> Response:
    if not _is_permitted(write=True):
        return _response_json(code=403, data={'msg': 'Not permitted'})

    job, valid = _validate_job(job)
    if not valid:
        return _response_json(code=400, data={'msg': 'Invalid job'})

    if _get_job_state(job) in ['running', 'activating', 'active']:
        return _response_json(code=425, data={'msg': 'Job is already active'})

    process(cmd=f"sudo systemctl start {job} --no-block", cwd='/tmp')
    return _response_json(code=200, data={'msg': 'Job started'})


@app.route('/api/job/<job>/state', methods=['GET'])
def api_get_job_status(job: str) -> Response:
    if not _is_permitted(write=False):
        return _response_json(code=403, data={'msg': 'Not permitted'})

    job, valid = _validate_job(job)
    if not valid:
        return _response_json(code=400, data={'msg': 'Invalid job'})

    return _response_json(code=200, data={'state': _get_job_state(job)})


@app.route('/api/job/<job>/tail', methods=['GET'])
def api_tail_job_logs(job: str) -> Response:
    if not _is_permitted(write=False):
        return _response_json(code=403, data={'msg': 'Not permitted'})

    job, valid = _validate_job(job)
    if not valid:
        return _response_json(code=400, data={'msg': 'Invalid job'})

    if not PATH_TAIL_CACHE.is_dir():
        PATH_TAIL_CACHE.mkdir()

    last_line = None
    cache_file = PATH_TAIL_CACHE / f'{job}.tail.log'
    if cache_file.is_file() and cache_file.stat().st_mtime > (time() - 60):
        with tail_lock:
            with open(cache_file, 'r', encoding='utf-8') as f:
                last_line = f.readline()

    last_run = _get_last_job_exec_id(job=job, force=True)
    logs_all = _get_job_logs(f"sudo journalctl {last_run} -n 1000 -u {job} {JCTL_FLAGS}")

    logs = []
    if last_line is None:
        logs = logs_all

    else:
        for i, l in enumerate(logs_all):
            if l == last_line:
                logs = logs_all[i+1:]
                break

    if len(logs) > 0:
        with tail_lock:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(logs[-1])

    logs = _clean_logs(logs)
    logs.reverse()
    return _response_json(code=200, data={'logs': logs})


@app.route('/api/job/<job>/logs', methods=['GET'])
def api_get_job_logs(job: str) -> Response:
    if not _is_permitted(write=False):
        return _response_json(code=403, data={'msg': 'Not permitted'})

    job, valid = _validate_job(job)
    if not valid:
        return _response_json(code=400, data={'msg': 'Invalid job'})

    l = 1000
    force_limit = False
    if 'lines' in request.args and request.args['lines'].isdigit():
        l = min(int(request.args['lines']), 20_000)
        force_limit = True

    last_run = _get_last_job_exec_id(job)
    if last_run == '':
        selector = f'-n {l}'

    else:
        selector = last_run
        if force_limit:
            selector += f' -n {l}'

    logs = _get_job_logs(f"sudo journalctl {selector} {JCTL_FLAGS}")
    logs = _clean_logs(logs)
    logs.reverse()
    return _response_json(code=200, data={'logs': logs})


@app.route('/')
def catch_base():
    return _response_json(
        code=200,
        data={
            'POST /api/job/<JOB>': 'Start a job',
            'GET /api/job/<JOB>/state': 'Get the current job-state',
            'GET /api/job/<JOB>/logs': 'Get job-logs. Optional parameters: lines (line count)',
            'GET /api/job/<JOB>/tail': 'Get the last lines of job-logs',
        },
    )


@app.route('/<path:path>')
def catch_all(path):
    del path
    return _response_json(code=400, data={'msg': 'Invalid request'})


if __name__ == '__main__':
    serve(app, host='127.0.0.1', port=8000)
