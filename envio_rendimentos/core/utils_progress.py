import threading
import uuid
from datetime import datetime
import json
import os
from django.conf import settings

_PROGRESS_STORE = {}
_PROGRESS_LOCK = threading.Lock()

# Reprocess jobs store: job_id -> metadata
_REPROCESS_JOBS = {}
_REPROCESS_LOCK = threading.Lock()

# Watchdog configuration
# Increase the heartbeat timeout to avoid false positives for long-running tasks
_HEARTBEAT_TIMEOUT = 600  # seconds without heartbeat considered stalled (10 minutes)
_FAIL_FAST_SECONDS = 900  # seconds to consider fail-fast when no progress and total==0 (15 minutes)
_WATCHDOG_INTERVAL = 10  # seconds between watchdog checks
_WATCHDOG_STARTED = False
_WATCHDOG_LOCK = threading.Lock()


def init_progress():
    request_id = str(uuid.uuid4())
    with _PROGRESS_LOCK:
        _PROGRESS_STORE[request_id] = {
            "status": "running",
            "percent": 0,
            "processed": 0,
            "total": 0,
            "current_credor": None,
            "logs": [],
            "errors": [],
            "credores": {},
            "started_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "finished_at": None,
            "estatisticas": {
                "sucessos": 0,
                "avisos": 0,
                "erros": 0
            }
        }
    # ensure processing dir exists
    processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing', request_id)
    os.makedirs(processing_dir, exist_ok=True)
    # ensure watchdog is running
    _start_watchdog_if_needed()
    return request_id


def log_progress(request_id, msg):
    with _PROGRESS_LOCK:
        if request_id not in _PROGRESS_STORE:
            return
        
        # Atualizar estatísticas
        stats = _PROGRESS_STORE[request_id]["estatisticas"]
        if "⚠️" in msg:
            stats["avisos"] += 1
        elif "❌" in msg:
            stats["erros"] += 1
        elif "✔" in msg or "🏁" in msg or "🎯" in msg or "✅" in msg:
            stats["sucessos"] += 1
        
        _PROGRESS_STORE[request_id]["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
        })
        # Atualizar heartbeat sempre que houver um log
        _PROGRESS_STORE[request_id]["last_heartbeat"] = datetime.now().isoformat()
    # persist snapshot
    try:
        _persist_progress(request_id)
    except Exception:
        pass


def _persist_errors(request_id):
    """Persist errors list to MEDIA_ROOT/processing/<request_id>/errors.json"""
    data = _PROGRESS_STORE.get(request_id)
    if not data:
        return
    errors = data.get('errors', [])
    path = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'errors.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
    except Exception:
        # Não interromper o processamento por falha ao persistir erros
        pass


def _persist_progress(request_id):
    """Persist a snapshot of the entire progress store for a request_id."""
    data = _PROGRESS_STORE.get(request_id)
    if not data:
        return
    path = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'progress.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_persisted_progress():
    """Load persisted progress snapshots from disk into the in-memory store."""
    processing_root = os.path.join(settings.MEDIA_ROOT, 'processing')
    if not os.path.exists(processing_root):
        return
    try:
        for name in os.listdir(processing_root):
            progress_path = os.path.join(processing_root, name, 'progress.json')
            if os.path.exists(progress_path):
                try:
                    with open(progress_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    with _PROGRESS_LOCK:
                        if name not in _PROGRESS_STORE:
                            # touch heartbeat so watchdog won't immediately mark as stalled
                            data.setdefault('last_heartbeat', datetime.now().isoformat())
                            data.setdefault('started_at', data.get('started_at') or datetime.now().isoformat())
                            _PROGRESS_STORE[name] = data
                except Exception:
                    continue
    except Exception:
        pass

# try to load any persisted progress on module import
_load_persisted_progress()


def resolve_errors_for_credor(request_id, slug):
    """Marca erros relacionados a um credor como resolvidos e persiste."""
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return
        changed = False
        for err in data.get('errors', []):
            # err.credor pode ser stored as slug or name; compare with slug
            if err.get('credor') == slug or slug in (err.get('credor_display','') or ''):
                if not err.get('resolved'):
                    err['resolved'] = True
                    changed = True
        if changed:
            try:
                _persist_errors(request_id)
            except Exception:
                pass


def get_errors(request_id):
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return []
        return data.get('errors', [])


# -----------------------
# Reprocess job helpers
# -----------------------

def start_reprocess_job(request_id, job_id, total):
    with _REPROCESS_LOCK:
        _REPROCESS_JOBS[job_id] = {
            'request_id': request_id,
            'status': 'running',
            'processed': 0,
            'total': total,
            'started_at': datetime.now().isoformat(),
            'finished_at': None,
            'logs': []
        }


def update_reprocess_job(job_id, *, processed=None, status=None, log_msg=None):
    with _REPROCESS_LOCK:
        job = _REPROCESS_JOBS.get(job_id)
        if not job:
            return
        if processed is not None:
            job['processed'] = processed
        if status is not None:
            job['status'] = status
            if status in ('completed', 'error'):
                job['finished_at'] = datetime.now().isoformat()
        if log_msg:
            job['logs'].append({'time': datetime.now().strftime('%H:%M:%S'), 'msg': log_msg})


def get_reprocess_job(job_id):
    with _REPROCESS_LOCK:
        return _REPROCESS_JOBS.get(job_id)


# -----------------------
# Heartbeat / Watchdog
# -----------------------

def _start_watchdog_if_needed():
    global _WATCHDOG_STARTED
    with _WATCHDOG_LOCK:
        if _WATCHDOG_STARTED:
            return
        _WATCHDOG_STARTED = True
        t = threading.Thread(target=_watchdog_loop, daemon=True)
        t.start()


def _watchdog_loop():
    """Background thread that marks stalled jobs as error after timeout."""
    import time as _time
    while True:
        try:
            now = datetime.now()
            with _PROGRESS_LOCK:
                items = list(_PROGRESS_STORE.items())
            for request_id, data in items:
                try:
                    if not data or data.get('status') != 'running':
                        continue
                    started = datetime.fromisoformat(data.get('started_at'))
                    last = datetime.fromisoformat(data.get('last_heartbeat')) if data.get('last_heartbeat') else started
                    age = (now - started).total_seconds()
                    idle = (now - last).total_seconds()

                    # Fail-fast: long-running with no progress and no total
                    if age > _FAIL_FAST_SECONDS and data.get('processed', 0) == 0 and data.get('total', 0) == 0:
                        log_progress(request_id, f"❌ Timeout: nenhum progresso detectado após {int(age)}s. Marcando erro.")
                        error_progress(request_id, 'Timeout: nenhum progresso detectado durante a leitura/parsing do arquivo')

                    # Heartbeat timeout: consider stalled
                    elif idle > _HEARTBEAT_TIMEOUT:
                        log_progress(request_id, f"❌ Heartbeat timeout: inativo há {int(idle)}s. Marcando erro.")

                        # Dump thread stacks to processing/<request_id>/stalled_traces.txt for debugging
                        try:
                            import sys, traceback
                            frames = sys._current_frames()
                            out_lines = []
                            out_lines.append(f"Stalled at {datetime.now().isoformat()}\n")
                            for tid, frame in frames.items():
                                out_lines.append(f"\n--- Thread {tid} ---\n")
                                out_lines.extend(traceback.format_stack(frame))
                            processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing', request_id)
                            os.makedirs(processing_dir, exist_ok=True)
                            trace_path = os.path.join(processing_dir, 'stalled_traces.txt')
                            with open(trace_path, 'w', encoding='utf-8') as tf:
                                tf.write('\n'.join(out_lines))
                            log_progress(request_id, f"🔍 Stack traces escritas em {trace_path}")
                        except Exception:
                            pass

                        error_progress(request_id, 'Processo possivelmente travado (heartbeat expirado)')
                except Exception:
                    # Não interromper o loop do watchdog por item com dados corruptos
                    continue
        except Exception:
            pass
        _time.sleep(_WATCHDOG_INTERVAL)


def finish_reprocess_job(job_id):
    with _REPROCESS_LOCK:
        job = _REPROCESS_JOBS.get(job_id)
        if not job:
            return
        job['status'] = 'completed'
        job['finished_at'] = datetime.now().isoformat()


def log_error(request_id, error_obj):
    """Append a structured error object to the progress store and persist to disk.

    error_obj should be a dict with keys: id, request_id, credor, credor_display, step,
    technical, friendly, type, time, retries, resolved
    """
    with _PROGRESS_LOCK:
        if request_id not in _PROGRESS_STORE:
            return
        data = _PROGRESS_STORE[request_id]
        data.setdefault('errors', []).append(error_obj)
        data['estatisticas']['erros'] += 1
        # Also register per-credor status
        if error_obj.get('credor'):
            cred_slug = error_obj.get('credor')
            cred = data.setdefault('credores', {}).get(cred_slug, {})
            cred.update({
                'status': 'ERROR',
                'last_error': error_obj.get('id'),
                'error_message': error_obj.get('friendly') or error_obj.get('technical'),
                'time': error_obj.get('time')
            })
            data['credores'][cred_slug] = cred
        # Also add a short message to logs for visibility
        data['logs'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'msg': f"❌ Erro ({error_obj.get('credor_display','?')}): {error_obj.get('friendly', error_obj.get('technical'))}"
        })
        # update heartbeat when error logged
        data['last_heartbeat'] = datetime.now().isoformat()
    # persist outside lock
    try:
        _persist_errors(request_id)
    except Exception:
        pass
    try:
        _persist_progress(request_id)
    except Exception:
        pass


def set_credor_status(request_id, slug, status, display=None, last_step=None, error_message=None, files=None):
    """Set per-credor status inside the progress store and persist credor meta.

    Status values: PENDING | PROCESSING | SUCCESS | ERROR
    """
    with _PROGRESS_LOCK:
        if request_id not in _PROGRESS_STORE:
            return
        data = _PROGRESS_STORE[request_id]
        cred = data.setdefault('credores', {}).get(slug, {})
        cred.update({
            'status': status,
            'display': display or cred.get('display'),
            'last_step': last_step or cred.get('last_step'),
            'error_message': error_message or cred.get('error_message'),
            'files': files or cred.get('files')
        })
        data['credores'][slug] = cred
        # touching heartbeat on explicit per-credor status changes
        data['last_heartbeat'] = datetime.now().isoformat()
    # persist credores metadata
    try:
        _persist_credores(request_id)
    except Exception:
        pass


def _persist_credores(request_id):
    data = _PROGRESS_STORE.get(request_id)
    if not data:
        return
    path = os.path.join(settings.MEDIA_ROOT, 'processing', request_id, 'credores.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data.get('credores', {}), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_credores(request_id, credores_map):
    """Initialize per-credor metadata entries.

    credores_map: dict slug -> display_name
    """
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return
        for slug, display in credores_map.items():
            data.setdefault('credores', {})[slug] = {
                'status': 'PENDING',
                'display': display,
                'last_step': None,
                'error_message': None,
                'files': None
            }
        data['last_heartbeat'] = datetime.now().isoformat()
    try:
        _persist_credores(request_id)
    except Exception:
        pass


def set_progress(request_id, *, processed=None, total=None, percent=None, credor=None):
    """Update global progress. Touches heartbeat when meaningful changes occur."""
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return

        changed = False
        if processed is not None and data.get('processed') != processed:
            data["processed"] = processed
            changed = True
        if total is not None and data.get('total') != total:
            data["total"] = total
            changed = True
        if percent is not None and data.get('percent') != percent:
            data["percent"] = percent
            changed = True
        if credor is not None and data.get('current_credor') != credor:
            data["current_credor"] = credor
            changed = True
        if changed:
            data['last_heartbeat'] = datetime.now().isoformat()
            # persist snapshot when meaningful changes happen
            try:
                _persist_progress(request_id)
            except Exception:
                pass


def finish_progress(request_id):
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return
        data["status"] = "completed"
        data["percent"] = 100
        data["finished_at"] = datetime.now().isoformat()
        data["last_heartbeat"] = datetime.now().isoformat()
    try:
        _persist_progress(request_id)
    except Exception:
        pass


def error_progress(request_id, error_msg):
    with _PROGRESS_LOCK:
        if request_id not in _PROGRESS_STORE:
            return
        _PROGRESS_STORE[request_id]["status"] = "error"
        _PROGRESS_STORE[request_id]["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": f"ERRO: {error_msg}",
        })
        _PROGRESS_STORE[request_id]["finished_at"] = datetime.now().isoformat()
    try:
        _persist_progress(request_id)
    except Exception:
        pass


def get_progress(request_id):
    with _PROGRESS_LOCK:
        return _PROGRESS_STORE.get(request_id)


def touch_heartbeat(request_id):
    """Touch heartbeat timestamp to indicate the job is alive."""
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return
        data['last_heartbeat'] = datetime.now().isoformat()

