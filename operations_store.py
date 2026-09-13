import csv
import io
import json
import os
import sqlite3
import uuid
from datetime import datetime


GROUP_STATES = ('CRIADO', 'CONFIGURANDO', 'AQUECIMENTO', 'PRONTO', 'DISTRIBUICAO', 'ATIVO')
CONTACT_STATES = ('pending', 'processing', 'completed', 'failed', 'retry')
JOB_STATES = ('pending', 'running', 'interrupted', 'completed', 'failed')


def utc_now():
    return datetime.utcnow().isoformat(timespec='seconds')


class OperationsStore:
    def __init__(self, data_dir):
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, 'operations.db')
        self.init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def init_db(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'OFF',
                    daily_limit INTEGER DEFAULT 40,
                    groups_created INTEGER DEFAULT 0,
                    actions_today INTEGER DEFAULT 0,
                    last_used_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    photo_path TEXT DEFAULT '',
                    state TEXT DEFAULT 'CRIADO',
                    session_name TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS warmup_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    duration_days INTEGER DEFAULT 10,
                    current_day INTEGER DEFAULT 1,
                    messages_per_day INTEGER DEFAULT 1,
                    photos_per_day INTEGER DEFAULT 0,
                    random_hours INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS warmup_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER NOT NULL,
                    day_number INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    payload TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    scheduled_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(campaign_id) REFERENCES warmup_campaigns(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS contact_imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    total_rows INTEGER DEFAULT 0,
                    valid_rows INTEGER DEFAULT 0,
                    duplicate_rows INTEGER DEFAULT 0,
                    invalid_rows INTEGER DEFAULT 0,
                    already_processed_rows INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id TEXT UNIQUE NOT NULL,
                    raw_value TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    username TEXT DEFAULT '',
                    status TEXT DEFAULT 'pending',
                    import_id INTEGER,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT '',
                    processed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(import_id) REFERENCES contact_imports(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);

                CREATE TABLE IF NOT EXISTS distribution_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_code TEXT UNIQUE NOT NULL,
                    group_id INTEGER,
                    session_name TEXT DEFAULT '',
                    expected_quantity INTEGER DEFAULT 30,
                    completed_quantity INTEGER DEFAULT 0,
                    pending_quantity INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    interrupted_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS job_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    contact_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT '',
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES distribution_jobs(id) ON DELETE CASCADE,
                    FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
                    UNIQUE(job_id, contact_id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    body TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    media_type TEXT DEFAULT 'image',
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT DEFAULT '',
                    action TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS checkpoints (
                    key TEXT PRIMARY KEY,
                    last_lead_id INTEGER,
                    last_group_id INTEGER,
                    last_session_name TEXT DEFAULT '',
                    processed_count INTEGER DEFAULT 0,
                    pending_count INTEGER DEFAULT 0,
                    payload TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                """
            )

    def dicts(self, rows):
        return [dict(row) for row in rows]

    def dashboard(self):
        with self.connect() as conn:
            contact_counts = {row['status']: row['total'] for row in conn.execute(
                'SELECT status, COUNT(*) total FROM contacts GROUP BY status'
            )}
            job_counts = {row['status']: row['total'] for row in conn.execute(
                'SELECT status, COUNT(*) total FROM distribution_jobs GROUP BY status'
            )}
            total_contacts = sum(contact_counts.values())
            processed = contact_counts.get('completed', 0) + contact_counts.get('failed', 0)
            pending = contact_counts.get('pending', 0) + contact_counts.get('retry', 0) + contact_counts.get('processing', 0)
            progress = round((processed / total_contacts) * 100, 2) if total_contacts else 0
            return {
                'sessions': conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],
                'groups': conn.execute('SELECT COUNT(*) FROM groups').fetchone()[0],
                'leads_imported': total_contacts,
                'processed': processed,
                'pending': pending,
                'errors': conn.execute('SELECT COUNT(*) FROM errors').fetchone()[0],
                'progress': progress,
                'contacts_by_status': contact_counts,
                'jobs_by_status': job_counts,
                'latest_jobs': self.dicts(conn.execute(
                    'SELECT * FROM distribution_jobs ORDER BY updated_at DESC LIMIT 8'
                )),
                'warmup': self.dicts(conn.execute(
                    """SELECT g.code, g.name, g.state, wc.current_day, wc.duration_days, wc.status
                       FROM warmup_campaigns wc
                       JOIN groups g ON g.id = wc.group_id
                       ORDER BY wc.updated_at DESC LIMIT 8"""
                )),
                'checkpoint': self.get_checkpoint(conn),
            }

    def get_checkpoint(self, conn=None):
        owns_conn = conn is None
        conn = conn or self.connect()
        try:
            row = conn.execute("SELECT * FROM checkpoints WHERE key = 'distribution'").fetchone()
            return dict(row) if row else {
                'last_lead_id': None,
                'last_group_id': None,
                'last_session_name': '',
                'processed_count': 0,
                'pending_count': 0,
            }
        finally:
            if owns_conn:
                conn.close()

    def sync_sessions(self, sessions):
        now = utc_now()
        with self.connect() as conn:
            for session in sessions:
                name = session.get('name') or session.get('session_name') or session.get('phone')
                if not name:
                    continue
                enabled = session.get('enabled', session.get('active', True))
                status = 'ON' if enabled else 'OFF'
                if session.get('flood_info') or session.get('limited'):
                    status = 'Limitada'
                conn.execute(
                    """INSERT INTO sessions(name, status, updated_at)
                       VALUES(?, ?, ?)
                       ON CONFLICT(name) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at""",
                    (name, status, now),
                )

    def list_groups(self):
        with self.connect() as conn:
            return self.dicts(conn.execute('SELECT * FROM groups ORDER BY id DESC LIMIT 200'))

    def upsert_group(self, payload):
        now = utc_now()
        code = payload.get('code') or f"GRUPO_{uuid.uuid4().hex[:8].upper()}"
        state = payload.get('state') or 'CRIADO'
        if state not in GROUP_STATES:
            state = 'CRIADO'
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO groups(code, name, description, photo_path, state, session_name, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(code) DO UPDATE SET
                     name=excluded.name, description=excluded.description, photo_path=excluded.photo_path,
                     state=excluded.state, session_name=excluded.session_name, updated_at=excluded.updated_at""",
                (
                    code,
                    payload.get('name') or code,
                    payload.get('description') or '',
                    payload.get('photo_path') or '',
                    state,
                    payload.get('session_name') or '',
                    now,
                    now,
                ),
            )
            row = conn.execute('SELECT * FROM groups WHERE code = ?', (code,)).fetchone()
            return dict(row)

    def create_warmup_campaign(self, group_id, duration_days=10, messages_per_day=1, photos_per_day=0, random_hours=True):
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                'UPDATE groups SET state = ?, updated_at = ? WHERE id = ?',
                ('AQUECIMENTO', now, group_id),
            )
            cur = conn.execute(
                """INSERT INTO warmup_campaigns(group_id, duration_days, current_day, messages_per_day,
                   photos_per_day, random_hours, status, started_at, updated_at)
                   VALUES(?, ?, 1, ?, ?, ?, 'running', ?, ?)""",
                (group_id, int(duration_days), int(messages_per_day), int(photos_per_day), 1 if random_hours else 0, now, now),
            )
            campaign_id = cur.lastrowid
            for day in range(1, int(duration_days) + 1):
                for index in range(int(messages_per_day)):
                    conn.execute(
                        'INSERT INTO warmup_tasks(campaign_id, day_number, task_type, payload, updated_at) VALUES(?, ?, ?, ?, ?)',
                        (campaign_id, day, 'message', json.dumps({'index': index + 1}), now),
                    )
                for index in range(int(photos_per_day)):
                    conn.execute(
                        'INSERT INTO warmup_tasks(campaign_id, day_number, task_type, payload, updated_at) VALUES(?, ?, ?, ?, ?)',
                        (campaign_id, day, 'photo', json.dumps({'index': index + 1}), now),
                    )
            return campaign_id

    def import_contacts(self, file_storage):
        filename = file_storage.filename or 'leads.txt'
        raw = file_storage.read().decode('utf-8-sig', errors='ignore')
        rows = self.parse_contacts(raw, filename)
        now = utc_now()
        seen = set()
        stats = {'total_rows': len(rows), 'valid_rows': 0, 'duplicate_rows': 0, 'invalid_rows': 0, 'already_processed_rows': 0}
        with self.connect() as conn:
            cur = conn.execute(
                'INSERT INTO contact_imports(filename, total_rows, created_at) VALUES(?, ?, ?)',
                (filename, len(rows), now),
            )
            import_id = cur.lastrowid
            for row in rows:
                external_id = row.get('external_id')
                if not external_id:
                    stats['invalid_rows'] += 1
                    continue
                if external_id in seen:
                    stats['duplicate_rows'] += 1
                    continue
                seen.add(external_id)
                existing = conn.execute('SELECT status FROM contacts WHERE external_id = ?', (external_id,)).fetchone()
                if existing:
                    if existing['status'] in ('completed', 'processing'):
                        stats['already_processed_rows'] += 1
                    else:
                        stats['duplicate_rows'] += 1
                    continue
                conn.execute(
                    """INSERT INTO contacts(external_id, raw_value, name, phone, username, status, import_id, updated_at)
                       VALUES(?, ?, ?, ?, ?, 'pending', ?, ?)""",
                    (external_id, row['raw_value'], row.get('name', ''), row.get('phone', ''), row.get('username', ''), import_id, now),
                )
                stats['valid_rows'] += 1
            conn.execute(
                """UPDATE contact_imports SET valid_rows=?, duplicate_rows=?, invalid_rows=?,
                   already_processed_rows=? WHERE id=?""",
                (stats['valid_rows'], stats['duplicate_rows'], stats['invalid_rows'], stats['already_processed_rows'], import_id),
            )
        return {'import_id': import_id, **stats}

    def parse_contacts(self, raw, filename):
        rows = []
        if filename.lower().endswith('.csv'):
            reader = csv.DictReader(io.StringIO(raw))
            for item in reader:
                value = item.get('phone') or item.get('telefone') or item.get('username') or item.get('user') or ''
                rows.append(self.normalize_contact(value, item))
        else:
            for line in raw.splitlines():
                rows.append(self.normalize_contact(line.strip(), {}))
        return rows

    def normalize_contact(self, value, item):
        value = (value or '').strip()
        username = value if value.startswith('@') else item.get('username', '')
        phone = ''.join(ch for ch in value if ch.isdigit() or ch == '+') if not username else item.get('phone', '')
        if username and len(username.strip('@')) >= 3:
            external_id = username.lower().strip()
        elif phone and len(''.join(ch for ch in phone if ch.isdigit())) >= 8:
            external_id = phone.strip()
        else:
            external_id = ''
        return {
            'external_id': external_id,
            'raw_value': value or json.dumps(item, ensure_ascii=False),
            'name': item.get('name') or item.get('nome') or '',
            'phone': phone,
            'username': username,
        }

    def create_distribution_job(self, payload):
        quantity = int(payload.get('quantity') or 30)
        group_code = payload.get('group_code') or ''
        session_name = payload.get('session_name') or ''
        now = utc_now()
        with self.connect() as conn:
            group = conn.execute('SELECT * FROM groups WHERE code = ?', (group_code,)).fetchone()
            if not group:
                group = self.upsert_group({'code': group_code or None, 'name': group_code or 'Grupo distribuição'})
                group_id = group['id']
            else:
                group_id = group['id']
            job_code = payload.get('job_code') or f"JOB #{uuid.uuid4().int % 100000:05d}"
            cur = conn.execute(
                """INSERT INTO distribution_jobs(job_code, group_id, session_name, expected_quantity,
                   pending_quantity, status, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (job_code, group_id, session_name, quantity, quantity, now, now),
            )
            job_id = cur.lastrowid
            contacts = conn.execute(
                "SELECT id FROM contacts WHERE status IN ('pending', 'retry') ORDER BY id LIMIT ?",
                (quantity,),
            ).fetchall()
            for contact in contacts:
                conn.execute(
                    'INSERT OR IGNORE INTO job_items(job_id, contact_id, status, updated_at) VALUES(?, ?, ?, ?)',
                    (job_id, contact['id'], 'pending', now),
                )
            pending = len(contacts)
            conn.execute(
                'UPDATE distribution_jobs SET pending_quantity=?, updated_at=? WHERE id=?',
                (pending, now, job_id),
            )
            self.update_checkpoint(conn, last_group_id=group_id, last_session_name=session_name)
            return dict(conn.execute('SELECT * FROM distribution_jobs WHERE id = ?', (job_id,)).fetchone())

    def resume_job(self, job_id):
        now = utc_now()
        with self.connect() as conn:
            job = conn.execute('SELECT * FROM distribution_jobs WHERE id = ?', (job_id,)).fetchone()
            if not job:
                return None
            conn.execute(
                "UPDATE distribution_jobs SET status='running', interrupted_at=NULL, updated_at=? WHERE id=?",
                (now, job_id),
            )
            conn.execute(
                "UPDATE job_items SET status='pending', updated_at=? WHERE job_id=? AND status IN ('processing', 'retry')",
                (now, job_id),
            )
            return dict(conn.execute('SELECT * FROM distribution_jobs WHERE id = ?', (job_id,)).fetchone())

    def interrupt_job(self, job_id):
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE distribution_jobs SET status='interrupted', interrupted_at=?, updated_at=? WHERE id=?",
                (now, now, job_id),
            )
            return dict(conn.execute('SELECT * FROM distribution_jobs WHERE id = ?', (job_id,)).fetchone())

    def list_jobs(self):
        with self.connect() as conn:
            return self.dicts(conn.execute(
                """SELECT dj.*, g.code group_code, g.name group_name
                   FROM distribution_jobs dj
                   LEFT JOIN groups g ON g.id = dj.group_id
                   ORDER BY dj.updated_at DESC LIMIT 100"""
            ))

    def update_checkpoint(self, conn, last_lead_id=None, last_group_id=None, last_session_name=None):
        counts = {row['status']: row['total'] for row in conn.execute('SELECT status, COUNT(*) total FROM contacts GROUP BY status')}
        processed = counts.get('completed', 0) + counts.get('failed', 0)
        pending = counts.get('pending', 0) + counts.get('retry', 0) + counts.get('processing', 0)
        current = conn.execute("SELECT * FROM checkpoints WHERE key='distribution'").fetchone()
        conn.execute(
            """INSERT INTO checkpoints(key, last_lead_id, last_group_id, last_session_name, processed_count, pending_count, updated_at)
               VALUES('distribution', ?, ?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                 last_lead_id=COALESCE(excluded.last_lead_id, checkpoints.last_lead_id),
                 last_group_id=COALESCE(excluded.last_group_id, checkpoints.last_group_id),
                 last_session_name=COALESCE(NULLIF(excluded.last_session_name, ''), checkpoints.last_session_name),
                 processed_count=excluded.processed_count,
                 pending_count=excluded.pending_count,
                 updated_at=excluded.updated_at""",
            (
                last_lead_id if last_lead_id is not None else (current['last_lead_id'] if current else None),
                last_group_id if last_group_id is not None else (current['last_group_id'] if current else None),
                last_session_name if last_session_name is not None else (current['last_session_name'] if current else ''),
                processed,
                pending,
                utc_now(),
            ),
        )
