"""Server-only recovery checks. No real Telegram clients or browser required."""
import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask, has_request_context

from group_campaigns import CampaignStore, campaign_loop, register_campaign_routes


class CampaignSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.users = ['alice', 'bob']
        self.stores = {}
        self.gateways = []
        self.invites = []
        self.locks = {}
        self.allowed = True
        self.api_available = True
        self.api_users = []
        owner = self

        class Gateway:
            def __init__(self, paths, sessions, api):
                self.paths = paths
                self.sessions = sessions
                self.api = api
                self.closed = threading.Event()
                owner.gateways.append(self)

            async def invite(self, group, name, payload, reserve_identity):
                owner.invites.append((Path(self.paths['data_dir']).name, payload['username']))
                return True

            async def close(self):
                self.closed.set()

        gateway_patch = patch('group_campaigns.TelegramCampaignGateway', Gateway)
        gateway_patch.start()
        self.addCleanup(gateway_patch.stop)

        class Sessions:
            def load_sessions(self, **kwargs):
                return [{'session_name': 'one.session', 'active': True}]

            def is_session_flooded(self, name):
                return False

        def background_api(username):
            self.assertFalse(has_request_context())
            self.api_users.append(username)
            return (1, username) if self.api_available else (None, None)

        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        self.supervisor = register_campaign_routes(
            self.app, lambda function: function, self.paths, lambda username: Sessions(),
            lambda: self.fail('Recovery attempted to read browser-session API credentials'),
            lambda *args, **kwargs: (self.allowed, 'Outra operação em andamento'),
            lambda kind, active, username: self.locks.update({username: active}),
            lambda username: {}, list_usernames=lambda: self.users,
            get_background_api=background_api,
        )
        self.supervisor.interval = 0.02
        self.addCleanup(self.shutdown)

    def paths(self, username):
        return {'data_dir': str(Path(self.temp.name) / username), 'sessions_dir': self.temp.name}

    def task(self, username='alice', status='running', error=''):
        store = self.stores.setdefault(username, CampaignStore(self.paths(username)['data_dir']))
        cid = store.create({'name': username, 'count': 1, 'delay_min': 1, 'delay_max': 1}, ['one.session'])
        group = store.groups(cid)[0]
        store.group_update(group['id'], status='ready')
        store.import_leads('leads.txt', b'@first_person\n@second_person', cid=cid)
        store.state(cid, status, error)
        return store, cid, group['id']

    def wait_for(self, predicate):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.fail('Server worker did not reach expected state')

    def shutdown(self):
        self.supervisor.stop()
        for store in self.stores.values():
            with store.db() as conn:
                conn.execute("UPDATE campaigns SET status='paused'")
        self.wait_for(lambda: not any(self.locks.values()))
        for gateway in self.gateways:
            gateway.closed.wait(2)

    def test_server_adds_without_login_or_any_http_request(self):
        store, cid, _ = self.task()
        self.supervisor.start()
        self.wait_for(lambda: store.snapshot()['campaigns'][0]['counts'].get('added') == 1)
        self.assertEqual(self.invites, [('alice', 'first_person')])
        self.assertEqual(self.api_users, ['alice'])
        self.assertEqual(store.get(cid)['status'], 'running')
        # Repeated startup/health scans must not duplicate a live executor.
        self.supervisor.start()
        self.supervisor.scan()
        self.assertEqual(len(self.gateways), 1)

    def test_explicit_pause_survives_restart_and_future_scans(self):
        store, cid, _ = self.task(status='paused')
        self.supervisor.start()
        self.supervisor.scan()
        self.assertEqual(store.get(cid)['status'], 'paused')
        self.assertEqual(self.gateways, [])

    def test_closing_authenticated_session_does_not_stop_additions(self):
        store, cid, _ = self.task()
        self.supervisor.start()
        self.wait_for(lambda: len(self.invites) == 1)
        client = self.app.test_client()
        with client.session_transaction() as browser_session:
            browser_session['username'] = 'alice'
        self.assertEqual(client.get('/api/group-campaigns').status_code, 200)
        with client.session_transaction() as browser_session:
            browser_session.clear()
        # No further requests: the next invitation must come from the server.
        self.wait_for(lambda: store.snapshot()['campaigns'][0]['counts'].get('added') == 2)
        self.assertEqual(store.get(cid)['status'], 'running')
        self.assertEqual(len(self.gateways), 1)

    def test_user_pause_stops_live_worker_and_supervisor_does_not_resume_it(self):
        store, cid, _ = self.task()
        self.supervisor.start()
        self.wait_for(lambda: bool(self.invites))
        client = self.app.test_client()
        with client.session_transaction() as browser_session:
            browser_session['username'] = 'alice'
        self.assertEqual(client.post(f'/api/group-campaigns/{cid}/pause').status_code, 200)
        self.wait_for(lambda: not self.locks.get('alice'))
        self.supervisor.scan()
        self.assertEqual(store.get(cid)['status'], 'paused')
        self.assertEqual(len(self.gateways), 1)

    def test_legacy_automatic_restart_pause_is_restored(self):
        store, cid, _ = self.task(status='paused', error='Servidor reiniciado. Clique em Iniciar para continuar.')
        self.supervisor.start()
        self.wait_for(lambda: bool(self.invites))
        self.assertEqual(store.get(cid)['status'], 'running')

    def test_restart_preserves_uncertain_invites_without_resending(self):
        store, cid, gid = self.task()
        pending = store.claim(cid, gid)
        self.supervisor.start()
        self.wait_for(lambda: store.snapshot()['campaigns'][0]['counts'].get('added') == 1)
        self.assertEqual(self.invites, [('alice', 'second_person')])
        with store.db() as conn:
            self.assertEqual(conn.execute('SELECT status FROM deliveries WHERE id=?', (pending['id'],)).fetchone()[0], 'unknown')

    def test_dead_executor_is_replaced_without_browser_polling(self):
        store, cid, gid = self.task()
        attempts = []

        async def crash_once(store, task_id, gateway):
            attempts.append(task_id)
            if len(attempts) == 1:
                store.claim(task_id, gid)
                await gateway.close()
                raise RuntimeError('Simulated executor exit')
            await campaign_loop(store, task_id, gateway)

        with patch('group_campaigns.campaign_loop', crash_once):
            self.supervisor.start()
            try:
                self.wait_for(lambda: store.snapshot()['campaigns'][0]['counts'].get('added') == 1)
                self.assertEqual(len(self.gateways), 2)
                self.assertEqual(self.invites, [('alice', 'second_person')])
                self.assertEqual(store.get(cid)['status'], 'running')
            finally:
                self.shutdown()

    def test_missing_api_is_retried_without_losing_running_intent(self):
        store, cid, _ = self.task()
        self.api_available = False
        self.supervisor.start()
        self.assertEqual(self.gateways, [])
        self.assertEqual(store.get(cid)['status'], 'running')
        self.api_available = True
        self.wait_for(lambda: bool(self.invites))

    def test_other_operation_lock_is_respected_then_retried(self):
        store, cid, _ = self.task()
        self.allowed = False
        self.supervisor.start()
        self.assertEqual(self.gateways, [])
        self.assertEqual(store.get(cid)['status'], 'running')
        self.allowed = True
        self.wait_for(lambda: bool(self.invites))

    def test_each_user_resumes_with_own_paths_api_and_leads(self):
        first, _, _ = self.task('alice')
        second, cid, _ = self.task('bob')
        second.import_leads('bob.txt', b'@bob_person', cid=cid)
        self.supervisor.start()
        self.wait_for(lambda: len(self.invites) >= 2)
        self.assertEqual(set(self.invites), {('alice', 'first_person'), ('bob', 'bob_person')})
        self.assertEqual({Path(g.paths['data_dir']).name: g.api for g in self.gateways},
                         {'alice': (1, 'alice'), 'bob': (1, 'bob')})

    def test_review_groups_are_not_recreated_automatically(self):
        store, cid, gid = self.task()
        store.group_update(gid, status='creating')
        self.supervisor.start()
        self.assertEqual(store.groups(cid)[0]['status'], 'error')
        self.assertEqual(store.get(cid)['status'], 'running')
        self.assertEqual(self.invites, [])


if __name__ == '__main__':
    unittest.main()
