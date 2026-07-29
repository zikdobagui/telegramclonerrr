import json
import os
import shutil
import tempfile
import threading
import time


_write_locks = {}
_write_locks_guard = threading.Lock()


def _get_write_lock(file_path):
    normalized_path = os.path.abspath(file_path)
    with _write_locks_guard:
        lock = _write_locks.get(normalized_path)
        if lock is None:
            lock = threading.RLock()
            _write_locks[normalized_path] = lock
        return lock


def load_json_file(file_path, default):
    """Carrega JSON e tenta recuperar do backup se o arquivo principal falhar."""
    if not os.path.exists(file_path):
        return default

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except Exception:
        backup_path = f'{file_path}.bak'
        if os.path.exists(backup_path):
            with open(backup_path, 'r', encoding='utf-8-sig') as f:
                content = f.read().strip()
                data = json.loads(content) if content else default
            atomic_write_json(file_path, data)
            return data
        raise


def atomic_write_json(file_path, data, indent=4):
    """Salva JSON sem risco de deixar o arquivo vazio se o processo cair."""
    directory = os.path.dirname(file_path) or '.'
    os.makedirs(directory, exist_ok=True)

    lock = _get_write_lock(file_path)
    with lock:
        backup_path = f'{file_path}.bak'
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                shutil.copy2(file_path, backup_path)
            except Exception:
                pass

        last_error = None
        for attempt in range(5):
            fd, temp_path = tempfile.mkstemp(prefix='.tmp_', suffix='.json', dir=directory)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=indent, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, file_path)
                return
            except PermissionError as error:
                last_error = error
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                time.sleep(0.15 * (attempt + 1))
            except Exception:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                raise

        raise last_error
