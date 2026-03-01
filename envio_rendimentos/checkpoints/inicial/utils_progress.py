import threading
import uuid
from datetime import datetime

_PROGRESS_STORE = {}
_PROGRESS_LOCK = threading.Lock()


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
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "estatisticas": {
                "sucessos": 0,
                "avisos": 0,
                "erros": 0
            }
        }
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
        elif "✔" in msg or "🏁" in msg or "🎯" in msg:
            stats["sucessos"] += 1
        
        _PROGRESS_STORE[request_id]["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
        })


def set_progress(request_id, *, processed=None, total=None, percent=None, credor=None):
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return

        if processed is not None:
            data["processed"] = processed
        if total is not None:
            data["total"] = total
        if percent is not None:
            data["percent"] = percent
        if credor is not None:
            data["current_credor"] = credor


def finish_progress(request_id):
    with _PROGRESS_LOCK:
        data = _PROGRESS_STORE.get(request_id)
        if not data:
            return
        data["status"] = "completed"
        data["percent"] = 100
        data["finished_at"] = datetime.now().isoformat()


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


def get_progress(request_id):
    with _PROGRESS_LOCK:
        return _PROGRESS_STORE.get(request_id)
