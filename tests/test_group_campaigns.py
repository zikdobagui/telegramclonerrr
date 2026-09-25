import asyncio
import io
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from flask import Flask
from group_campaigns import CampaignStore, TelegramCampaignGateway, campaign_loop, register_campaign_routes


class InviteResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_promotion_uses_creator_and_limited_rights(self):
        from telethon.tl.types import InputUser
        gateway = TelegramCampaignGateway({}, {}, ())
        client = AsyncMock()
        client.get_input_entity.return_value = InputUser(123, 456)
        gateway.peer = AsyncMock(return_value=(client, 'peer'))
        group = {'creator': 'owner.session'}
        await gateway.promote_admin(group, 'example_user')
        gateway.peer.assert_awaited_once_with(group, 'owner.session')
        request = client.await_args.args[0]
        self.assertTrue(request.admin_rights.ban_users)
        self.assertFalse(request.admin_rights.add_admins)
        client.get_input_entity.assert_awaited_once_with('@example_user')

    async def test_legacy_and_wrapped_join_results(self):
        chat = SimpleNamespace(id=123)
        legacy = SimpleNamespace(chats=[chat], updates=[])
        wrapped = type('ChatInviteJoinResultOk', (), {'updates': legacy})()
        gateway = TelegramCampaignGateway({}, {}, ())
        for result in (legacy, wrapped):
            with self.subTest(result=type(result).__name__):
                client = AsyncMock(side_effect=[SimpleNamespace(), result])
                self.assertIs(await gateway.resolve(client, 'https://t.me/+example'), chat)
                self.assertEqual(client.await_count, 2)

    async def test_missing_chats_rechecks_membership_without_rejoining(self):
        from telethon.tl.types import ChatInviteAlready
        chat = SimpleNamespace(id=123)
        client = AsyncMock(side_effect=[SimpleNamespace(), SimpleNamespace(updates=[]), ChatInviteAlready(chat)])
        gateway = TelegramCampaignGateway({}, {}, ())
        self.assertIs(await gateway.resolve(client, 'https://t.me/+example'), chat)
        self.assertEqual([type(call.args[0]).__name__ for call in client.await_args_list],
                         ['CheckChatInviteRequest', 'ImportChatInviteRequest', 'CheckChatInviteRequest'])

    async def test_pending_verification_is_not_treated_as_joined(self):
        gateway = TelegramCampaignGateway({}, {}, ())
        client = AsyncMock(side_effect=[SimpleNamespace(), SimpleNamespace(), SimpleNamespace()])
        with self.assertRaisesRegex(ValueError, 'ainda não confirmada'):
            await gateway.resolve(client, 'https://t.me/+example')


class CampaignStoreTests(unittest.TestCase):
    def test_admin_username_is_validated_and_saved(self):
        cid = self.store.create({'name': 'Admin', 'admin_username': ' @example_user '}, ['one'])
        self.assertEqual(self.store.get(cid)['settings']['admin_username'], 'example_user')
        with self.assertRaises(ValueError):
            self.store.create({'name': 'Invalid', 'admin_username': 'https://t.me/example'}, ['one'])

    def test_resume_generic_request_error_preserves_uncertain_delivery(self):
        cid, groups = self.task()
        self.leads(2)
        delivery = self.store.claim(cid, groups[0]['id'])
        self.store.finish(delivery['id'], 'unknown')
        for group in groups:
            self.store.group_update(group['id'], status='error', channel_id='123', access_hash='456',
                                    creator='one.session', invite='https://t.me/+existing',
                                    error='Request was unsuccessful 1 time(s)')
        self.store.state(cid, 'paused')
        self.store.prepare_start(cid)
        self.assertTrue(all(g['status'] == 'ready' for g in self.store.groups(cid)))
        self.assertIsNone(self.store.claim(cid, groups[0]['id']))
        self.assertEqual(self.store.snapshot()['campaigns'][0]['counts'], {'unknown': 1})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = CampaignStore(self.temp.name)

    def task(self, **values):
        cid = self.store.create(dict(name='Teste', count=2, daily_limit=1, **values), ['one.session', 'two.session'])
        for group in self.store.groups(cid):
            self.store.group_update(group['id'], status='ready')
        self.store.state(cid, 'running')
        return cid, self.store.groups(cid)

    def leads(self, count=10):
        return self.store.import_leads('leads.json', json.dumps({'members': [{'id': 100 + n, 'username': f'lead_{n}', 'access_hash': 9000000000000000000 + n} for n in range(count)]}).encode())

    def test_resume_recovers_invite_error_without_resetting_leads_or_quota(self):
        cid, groups = self.task()
        self.leads(2)
        delivery = self.store.claim(cid, groups[0]['id'])
        self.store.finish(delivery['id'], 'unknown')
        for group in groups:
            self.store.group_update(group['id'], status='error', channel_id=str(1000 + group['id']),
                                    access_hash='123', creator='one.session', invite='https://t.me/+existing',
                                    error="'ChatInviteJoinResultOk' object has no attribute 'chats'")
        self.store.state(cid, 'paused', 'Todos os grupos precisam de revisão ou substituição.')
        self.store.prepare_start(cid)
        self.assertEqual(self.store.get(cid)['status'], 'running')
        self.assertTrue(all(group['status'] == 'ready' and not group['error'] for group in self.store.groups(cid)))
        self.assertEqual([group['id'] for group in self.store.groups(cid)], [group['id'] for group in groups])
        self.assertIsNone(self.store.claim(cid, groups[0]['id']))
        self.assertEqual(self.store.snapshot()['campaigns'][0]['counts'], {'unknown': 1})

    def test_resume_preserves_warmup_and_rejects_unrelated_errors(self):
        import time
        cid, groups = self.task(warming=True, messages='Olá')
        until = time.time() + 3600
        self.store.group_update(groups[0]['id'], status='error', channel_id='123', access_hash='456',
                                creator='one.session', invite='https://t.me/+existing', warm_until=until,
                                error="'ChatInviteJoinResultOk' object has no attribute 'chats'")
        self.store.group_update(groups[1]['id'], status='error', error='CHANNEL_PRIVATE')
        self.store.state(cid, 'paused')
        self.store.prepare_start(cid)
        current = self.store.groups(cid)
        self.assertEqual(current[0]['status'], 'warming')
        self.assertEqual(current[0]['warm_until'], until)
        self.assertEqual(current[1]['status'], 'error')
        self.store.group_update(groups[0]['id'], status='error', error='CHANNEL_PRIVATE')
        self.store.state(cid, 'paused')
        with self.assertRaisesRegex(ValueError, 'Nenhum grupo disponível'):
            self.store.prepare_start(cid)
        self.assertEqual(self.store.get(cid)['status'], 'paused')

    def test_import_is_additive_and_deduplicates_aliases(self):
        self.assertEqual(self.leads(3)['added'], 3)
        self.assertEqual(self.leads(5)['added'], 2)
        self.assertEqual(self.store.import_leads('leads.txt', b'@LEAD_0\nhttps://t.me/lead_1\nnot valid')['duplicates'], 2)
        self.assertEqual(self.store.snapshot()['total_leads'], 5)
        with self.store.db() as conn:
            payload = json.loads(conn.execute('SELECT payload FROM leads LIMIT 1').fetchone()[0])
            self.assertEqual(payload['access_hash'], 9000000000000000000)

    def test_parallel_claims_respect_daily_quota_and_unique_leads(self):
        cid, groups = self.task()
        self.leads()
        with ThreadPoolExecutor(max_workers=8) as pool:
            reservations = list(pool.map(lambda index: self.store.claim(cid, groups[index % 2]['id']), range(20)))
        reserved = [item for item in reservations if item]
        self.assertEqual(len(reserved), 2)
        self.assertEqual(len({item['lead_id'] for item in reserved}), 2)

    def test_enriched_import_merges_identities_without_reusing_delivered_lead(self):
        cid, groups = self.task()
        self.store.import_leads('leads.json', b'[{"id":123}]')
        self.store.import_leads('leads.txt', b'@same_lead')
        reserved = self.store.claim(cid, groups[0]['id'])
        self.store.finish(reserved['id'], 'added')
        self.store.import_leads('leads.json', b'[{"id":123,"username":"same_lead"}]')
        self.assertEqual(self.store.snapshot()['total_leads'], 1)
        self.assertIsNone(self.store.claim(cid, groups[1]['id']))

    def test_replacement_preserves_history_and_daily_quota(self):
        cid, groups = self.task()
        self.leads()
        first = self.store.claim(cid, groups[0]['id'])
        self.store.finish(first['id'], 'added')
        self.store.state(cid, 'paused')
        self.store.edit_group(cid, groups[0]['id'], {'replace': True, 'reference': 'https://t.me/+example'})
        new_group = self.store.groups(cid)[0]
        self.store.group_update(new_group['id'], status='ready')
        self.store.state(cid, 'running')
        self.assertIsNone(self.store.claim(cid, new_group['id']))
        with patch('group_campaigns.day_key', return_value='2099-01-01'):
            second = self.store.claim(cid, new_group['id'])
        self.assertNotEqual(first['lead_id'], second['lead_id'])
        with self.store.db() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM groups').fetchone()[0], 3)

    def test_per_group_dedup_allows_one_delivery_in_each_slot(self):
        cid, groups = self.task(dedup='group')
        self.leads(1)
        first = self.store.claim(cid, groups[0]['id'])
        second = self.store.claim(cid, groups[1]['id'])
        self.assertEqual(first['lead_id'], second['lead_id'])

    def test_task_daily_limit_spans_groups(self):
        cid, groups = self.task(limit_scope='task')
        self.leads()
        self.assertIsNotNone(self.store.claim(cid, groups[0]['id']))
        self.assertIsNone(self.store.claim(cid, groups[1]['id']))

    def test_resolved_telegram_identity_cannot_be_sent_twice(self):
        cid, groups = self.task()
        self.leads(2)
        first = self.store.claim(cid, groups[0]['id'])
        second = self.store.claim(cid, groups[1]['id'])
        self.assertTrue(self.store.reserve_identity(first['id'], 123456))
        self.assertFalse(self.store.reserve_identity(second['id'], 123456))

    def test_restart_keeps_unknown_leads_reserved(self):
        cid, groups = self.task()
        self.leads()
        first = self.store.claim(cid, groups[0]['id'])
        self.store.group_update(groups[1]['id'], status='creating')
        restarted = CampaignStore(self.temp.name)
        restarted.recover()
        self.assertEqual(restarted.get(cid)['status'], 'paused')
        self.assertEqual(restarted.groups(cid)[1]['status'], 'error')
        self.assertEqual(restarted.snapshot()['campaigns'][0]['counts'], {'unknown': 1})
        restarted.state(cid, 'running')
        with patch('group_campaigns.day_key', return_value='2099-01-01'):
            second = restarted.claim(cid, groups[0]['id'])
        self.assertNotEqual(first['lead_id'], second['lead_id'])

    def test_new_leads_can_be_consumed_by_waiting_task(self):
        cid, groups = self.task()
        self.assertIsNone(self.store.claim(cid, groups[0]['id']))
        self.leads(1)
        self.assertIsNotNone(self.store.claim(cid, groups[0]['id']))

    def test_user_databases_are_isolated(self):
        self.leads()
        other = CampaignStore(str(Path(self.temp.name) / 'other'))
        self.assertEqual(other.snapshot()['total_leads'], 0)

    def test_cannot_replace_running_or_foreign_group(self):
        cid, groups = self.task()
        with self.assertRaises(ValueError):
            self.store.edit_group(cid, groups[0]['id'], {'replace': True})
        other, _ = self.task()
        self.store.state(other, 'paused')
        with self.assertRaises(ValueError):
            self.store.edit_group(other, groups[0]['id'], {'replace': True})

    def test_runner_creates_warms_and_distributes(self):
        cid = self.store.create({'name': 'Teste', 'count': 1, 'warming': True, 'messages': 'Olá\nBem-vindo'}, ['one.session'])
        self.leads(1)
        self.store.state(cid, 'running')
        store = self.store
        calls = []

        class Gateway:
            async def create(self, group, name, persist):
                calls.append('create')
                persist(channel_id='100', access_hash='123', creator=name)
                return {'channel_id': '100', 'access_hash': '123', 'creator': name, 'invite': 'https://t.me/+test'}

            async def warm(self, group, name, phrase):
                calls.append('warm')
                store.group_update(group['id'], warm_until=1)

            async def invite(self, group, name, payload, reserve_identity):
                calls.append('invite')
                assert reserve_identity(payload['id'])
                store.state(cid, 'paused')
                return True

            async def close(self):
                calls.append('close')

        # Fast-forward waits; no Telegram requests are made.
        with patch('group_campaigns.time.monotonic', side_effect=(n * 10000 for n in range(1000))):
            asyncio.run(campaign_loop(store, cid, Gateway()))
        self.assertEqual(calls, ['create', 'warm', 'invite', 'close'])
        self.assertEqual(store.snapshot()['campaigns'][0]['counts'], {'added': 1})

    def test_unknown_invite_result_is_not_retried(self):
        cid = self.store.create({'name': 'Teste', 'count': 1}, ['one.session'])
        group = self.store.groups(cid)[0]
        self.store.group_update(group['id'], status='ready')
        self.store.state(cid, 'running')
        self.leads(1)

        class Gateway:
            async def invite(self, group, name, payload, reserve_identity):
                assert reserve_identity(payload['id'])
                raise TimeoutError('Resposta perdida')

            async def close(self):
                pass

        with patch('group_campaigns.time.monotonic', side_effect=(n * 10000 for n in range(1000))):
            asyncio.run(campaign_loop(self.store, cid, Gateway()))
        self.assertEqual(self.store.get(cid)['status'], 'paused')
        self.assertEqual(self.store.snapshot()['campaigns'][0]['counts'], {'unknown': 1})
        self.store.state(cid, 'running')
        self.store.group_update(group['id'], status='ready')
        with patch('group_campaigns.day_key', return_value='2099-01-01'):
            self.assertIsNone(self.store.claim(cid, group['id']))


class CampaignApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        app = Flask(__name__)
        app.secret_key = 'test-only'
        self.app = app
        from functools import wraps
        from flask import session, jsonify

        def authenticated(function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                if 'username' not in session:
                    return jsonify(success=False), 401
                return function(*args, **kwargs)
            return wrapped

        class Sessions:
            def load_sessions(self, **kwargs):
                return [{'session_name': 'one.session', 'active': True}]

            def is_session_flooded(self, name):
                return False

        register_campaign_routes(app, authenticated,
                                 lambda username: {'data_dir': str(Path(self.temp.name) / username), 'sessions_dir': self.temp.name},
                                 lambda username: Sessions(), lambda: (1, 'test'),
                                 lambda *args, **kwargs: (True, 'OK'), lambda *args, **kwargs: None,
                                 lambda username: {})
        self.client = app.test_client()

    def login(self, username):
        with self.client.session_transaction() as session:
            session['username'] = username

    def test_authentication_validation_import_and_user_isolation(self):
        self.assertEqual(self.client.get('/api/group-campaigns').status_code, 401)
        self.login('alice')
        bad = self.client.post('/api/group-campaigns', json={'name': 'Task', 'sessions': ['invalid']})
        self.assertEqual(bad.status_code, 400)
        created = self.client.post('/api/group-campaigns', json={'name': 'Task', 'count': 10, 'sessions': ['one.session']})
        self.assertTrue(created.json['success'])
        imported = self.client.post('/api/group-campaigns/leads', data={'file': (io.BytesIO(b'@some_lead'), 'leads.txt')})
        self.assertEqual(imported.json['added'], 1)
        snapshot = self.client.get('/api/group-campaigns').json
        self.assertEqual(len(snapshot['campaigns'][0]['groups']), 10)
        self.login('bob')
        self.assertEqual(self.client.get('/api/group-campaigns').json['total_leads'], 0)
        self.assertEqual(self.client.post('/api/group-campaigns/1/pause').status_code, 400)

    def test_start_and_pause_control_worker_without_telegram(self):
        self.login('alice')
        cid = self.client.post('/api/group-campaigns', json={'name': 'Task', 'sessions': ['one.session']}).json['id']
        started, stopped = threading.Event(), threading.Event()

        async def fake_loop(store, task_id, gateway):
            started.set()
            while store.get(task_id)['status'] == 'running':
                await asyncio.sleep(0.01)
            stopped.set()

        with patch('group_campaigns.campaign_loop', fake_loop), patch('group_campaigns.TelegramCampaignGateway'):
            self.assertTrue(self.client.post(f'/api/group-campaigns/{cid}/start').json['success'])
            self.assertTrue(started.wait(5))
            try:
                self.assertEqual(self.client.post(f'/api/group-campaigns/{cid}/start').status_code, 400)
                self.assertEqual(self.client.put(f'/api/group-campaigns/{cid}/groups/1', json={'replace': True}).status_code, 400)
            finally:
                self.assertTrue(self.client.post(f'/api/group-campaigns/{cid}/pause').json['success'])
                self.assertTrue(stopped.wait(5))


if __name__ == '__main__':
    unittest.main()
