"""Real SQLite snapshots and mocked Telegram; never reads production sessions."""
import asyncio
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from extractor import MemberExtractor, snapshot_session


class SessionSnapshotTests(unittest.TestCase):
    def test_real_telethon_session_keeps_authorization_and_private_group_cache(self):
        from telethon.crypto import AuthKey
        from telethon.sessions import SQLiteSession
        from telethon.tl.types import InputPeerChannel
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'original.session'
            destination = Path(directory) / 'copy.session'
            original = SQLiteSession(str(source))
            original.set_dc(2, '149.154.167.51', 443)
            original.auth_key = AuthKey(bytes(range(256)))
            original.process_entities([InputPeerChannel(123, 456)])
            original.save()
            original.close()
            snapshot_session(source, destination)
            copied = SQLiteSession(str(destination))
            try:
                self.assertEqual(copied.auth_key.key, bytes(range(256)))
                self.assertEqual(copied.dc_id, 2)
                self.assertEqual(copied.get_input_entity(-1000000000123).access_hash, 456)
            finally:
                copied.close()

    def test_backup_includes_committed_wal_while_original_has_a_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'original.session'
            destination = Path(directory) / 'copy.session'
            conn = sqlite3.connect(source)
            self.addCleanup(conn.close)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE entities(id INTEGER PRIMARY KEY, name TEXT)')
            conn.execute("INSERT INTO entities VALUES(1,'committed')")
            conn.commit()
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("UPDATE entities SET name='uncommitted' WHERE id=1")
            snapshot_session(source, destination)
            copy = sqlite3.connect(destination)
            try:
                self.assertEqual(copy.execute('SELECT name FROM entities').fetchone()[0], 'committed')
                copy.execute("UPDATE entities SET name='extracted' WHERE id=1")
                copy.commit()
            finally:
                copy.close()
            self.assertEqual(conn.execute('SELECT name FROM entities').fetchone()[0], 'uncommitted')
            conn.rollback()
            conn.close()

    def test_missing_source_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'missing.session'
            with self.assertRaises(sqlite3.OperationalError):
                snapshot_session(source, Path(directory) / 'copy.session')
            self.assertFalse(source.exists())

    def test_exclusive_lock_has_a_bounded_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'locked.session'
            conn = sqlite3.connect(source)
            try:
                conn.execute('CREATE TABLE test(id INTEGER)')
                conn.commit()
                conn.execute('BEGIN EXCLUSIVE')
                with self.assertRaises(TimeoutError):
                    snapshot_session(source, Path(directory) / 'copy.session', timeout=.02)
            finally:
                conn.close()


class ExtractionDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'original.session'
        conn = sqlite3.connect(self.source)
        conn.execute('CREATE TABLE marker(value TEXT)')
        conn.execute("INSERT INTO marker VALUES('original')")
        conn.commit()
        conn.close()
        self.info = {'session_name': 'original.session', 'session_path': str(self.source)}
        self.extractor = MemberExtractor(1, 'test', self.temp.name, str(Path(self.temp.name) / 'members.json'))

    async def test_success_writes_only_private_database_and_disconnects_once(self):
        client = AsyncMock()
        client.is_user_authorized.return_value = True
        client.get_me.return_value = SimpleNamespace(id=1, first_name='Example', username='example')
        client.get_entity.return_value = SimpleNamespace(id=10, access_hash=20, title='Group')
        user = SimpleNamespace(id=2, access_hash=30, username='member', first_name='Member', last_name='', phone='', bot=False, deleted=False)
        client.return_value = SimpleNamespace(users=[user])

        async def no_admins(*args, **kwargs):
            for item in ():
                yield item

        client.iter_participants = no_admins
        private = []

        def factory(path, *args):
            private.append(Path(path))
            conn = sqlite3.connect(path)
            conn.execute("UPDATE marker SET value='changed by extraction'")
            conn.commit()
            conn.close()
            return client

        with patch('telethon.TelegramClient', side_effect=factory):
            members = await self.extractor._extract_async(self.info, '@example_group')
        self.assertEqual(len(members), 1, self.extractor.last_error)
        client.disconnect.assert_awaited_once()
        self.assertNotEqual(private[0], self.source)
        self.assertFalse(private[0].parent.exists())
        conn = sqlite3.connect(self.source)
        try:
            self.assertEqual(conn.execute('SELECT value FROM marker').fetchone()[0], 'original')
        finally:
            conn.close()

    async def test_unauthorized_session_is_closed_once_and_reports_failure(self):
        client = AsyncMock()
        client.is_user_authorized.return_value = False
        with patch('telethon.TelegramClient', return_value=client) as factory:
            self.assertEqual(await self.extractor._extract_async(self.info, '@example_group'), [])
        self.assertIn('não autorizada', self.extractor.last_error)
        client.disconnect.assert_awaited_once()
        self.assertFalse(Path(factory.call_args.args[0]).parent.exists())

    async def test_constructor_failure_removes_private_database(self):
        paths = []

        def fail(path, *args):
            paths.append(Path(path))
            raise RuntimeError('constructor failed')

        with patch('telethon.TelegramClient', side_effect=fail):
            self.assertEqual(await self.extractor._extract_async(self.info, '@example_group'), [])
        self.assertEqual(self.extractor.last_error, 'constructor failed')
        self.assertFalse(paths[0].parent.exists())


class ExtractionConcurrencyTests(unittest.TestCase):
    def test_same_session_cannot_run_two_extractions_even_with_different_path_forms(self):
        with tempfile.TemporaryDirectory() as directory:
            started, release = threading.Event(), threading.Event()
            first, second = MemberExtractor(1, 'test'), MemberExtractor(1, 'test')

            async def blocked(*args):
                started.set()
                while not release.is_set():
                    await asyncio.sleep(.01)
                return []

            first._extract_async = blocked
            path = str(Path(directory) / 'same')
            worker = threading.Thread(target=first.extract_members, args=({'session_path': path}, '@group'))
            worker.start()
            try:
                self.assertTrue(started.wait(3))
                self.assertEqual(second.extract_members({'session_path': path + '.session'}, '@group'), [])
                self.assertIn('já está extraindo', second.last_error)
            finally:
                release.set()
                worker.join(3)
            second._extract_async = AsyncMock(return_value=[{'id': 1}])
            self.assertEqual(second.extract_members({'session_path': path}, '@group'), [{'id': 1}])
