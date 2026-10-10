"""Permanent group deletion tests, with no real Telegram connection."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from flask import Flask, session
from telethon.errors import ChatAdminRequiredError, ChannelPrivateError
from telethon.tl.functions.channels import DeleteChannelRequest
from telethon.tl.types import ChannelParticipantCreator, ChatAdminRights

from group_campaigns import CampaignStore, TelegramCampaignGateway, register_campaign_routes


class DeleteGroupGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_checks_owner_and_records_attempt_before_deleting(self):
        gateway = TelegramCampaignGateway({}, {}, ())
        client = AsyncMock(side_effect=[SimpleNamespace(participant=ChannelParticipantCreator(1, ChatAdminRights())), SimpleNamespace()])
        gateway.peer = AsyncMock(return_value=(client, 'peer'))
        before_send = Mock(side_effect=lambda: self.assertEqual(client.await_count, 1))
        await gateway.delete_group({'creator': 'creator.session'}, before_send)
        gateway.peer.assert_awaited_once_with({'creator': 'creator.session'}, 'creator.session')
        before_send.assert_called_once_with()
        self.assertIsInstance(client.await_args.args[0], DeleteChannelRequest)
        self.assertEqual(client.await_args.args[0].channel, 'peer')

    async def test_non_owner_does_not_send_delete(self):
        gateway = TelegramCampaignGateway({}, {}, ())
        client = AsyncMock(return_value=SimpleNamespace(participant=object()))
        gateway.peer = AsyncMock(return_value=(client, 'peer'))
        before_send = Mock()
        with self.assertRaisesRegex(ValueError, 'dono atual'):
            await gateway.delete_group({'creator': 'creator.session'}, before_send)
        self.assertEqual(client.await_count, 1)
        before_send.assert_not_called()


class DeleteGroupApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        from functools import wraps

        def authenticated(function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                if 'username' not in session:
                    return {'success': False}, 401
                return function(*args, **kwargs)
            return wrapped

        manager = SimpleNamespace(load_sessions=lambda **_: [{'session_name': 'owner.session', 'active': True}], is_session_flooded=lambda _: False)
        self.set_lock = Mock()
        register_campaign_routes(self.app, authenticated,
                                 lambda user: {'data_dir': str(Path(self.temp.name) / user)},
                                 lambda _: manager, lambda: (1, 'api-hash'),
                                 lambda *args, **kwargs: (True, ''), self.set_lock, lambda _: {})
        self.client = self.app.test_client()
        with self.client.session_transaction() as saved:
            saved['username'] = 'alice'
        self.cid = self.client.post('/api/group-campaigns', json={'name': 'Group', 'count': 1, 'sessions': ['owner.session']}).json['id']
        self.store = CampaignStore(str(Path(self.temp.name) / 'alice'))
        group = self.store.groups(self.cid)[0]
        self.gid = group['id']
        self.store.group_update(self.gid, status='ready', channel_id='10', access_hash='20', creator='owner.session')
        self.url = f'/api/group-campaigns/{self.cid}/groups/{self.gid}'
        self.payload = {'confirmed': True, 'title': group['title'], 'channel_id': '10'}
        self.gateway = SimpleNamespace(delete_group=AsyncMock(side_effect=self.delete_group), close=AsyncMock())

    async def delete_group(self, group, before_send):
        before_send()

    def delete(self, **changes):
        return self.client.delete(self.url, json={**self.payload, **changes})

    def test_confirmed_deletion_removes_group_but_keeps_leads_and_history(self):
        self.store.import_leads('leads.txt', b'@some_user')
        self.store.state(self.cid, 'running')
        delivery = self.store.claim(self.cid, self.gid)
        self.store.finish(delivery['id'], 'added')
        self.store.state(self.cid, 'paused')
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.delete().status_code, 200)
            self.assertEqual(self.delete().status_code, 400)
        self.assertEqual(self.store.groups(self.cid), [])
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['total_leads'], 1)
        self.assertEqual(snapshot['campaigns'][0]['counts'], {'added': 1})
        self.assertIn('excluído do Telegram', snapshot['campaigns'][0]['events'][0]['message'])
        with self.assertRaises(ValueError):
            self.store.prepare_start(self.cid)
        self.gateway.delete_group.assert_awaited_once()
        self.gateway.close.assert_awaited_once()
        self.set_lock.assert_called_with('group_campaign', False, username='alice')

    def test_requires_confirmation_current_group_and_paused_task(self):
        with patch('group_campaigns.TelegramCampaignGateway') as factory:
            self.assertEqual(self.delete(confirmed=False).status_code, 400)
            self.assertEqual(self.delete(title='Wrong group').status_code, 400)
            self.assertEqual(self.delete(channel_id='999').status_code, 400)
            self.store.state(self.cid, 'running')
            self.assertEqual(self.delete().status_code, 400)
            self.store.state(self.cid, 'paused')
            self.store.edit_group(self.cid, self.gid, {'replace': True})
            self.assertEqual(self.delete().status_code, 400)
            factory.assert_not_called()

    def test_authentication_and_user_isolation(self):
        with patch('group_campaigns.TelegramCampaignGateway') as factory:
            with self.client.session_transaction() as saved:
                saved['username'] = 'bob'
            self.assertEqual(self.delete().status_code, 400)
            with self.client.session_transaction() as saved:
                saved.clear()
            self.assertEqual(self.delete().status_code, 401)
            factory.assert_not_called()

    def test_permission_failure_preserves_group_and_restores_status(self):
        async def rejected(*args):
            await self.delete_group(*args)
            raise ChatAdminRequiredError(request=None)
        self.gateway.delete_group.side_effect = rejected
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.delete().status_code, 400)
        group = self.store.groups(self.cid)[0]
        self.assertEqual(group['status'], 'ready')
        self.assertEqual(group['deletion_status'], 'failed')

    def test_lost_response_keeps_group_and_restart_does_not_retry(self):
        async def timeout(*args):
            await self.delete_group(*args)
            raise TimeoutError('response lost')
        self.gateway.delete_group.side_effect = timeout
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.delete().status_code, 400)
            self.store.recover()
            group = self.store.groups(self.cid)[0]
            self.assertEqual(group['status'], 'error')
            self.assertEqual(group['deletion_status'], 'unknown')
            self.assertEqual(self.client.post(self.url + '/ownership', json={}).status_code, 400)
            with self.assertRaises(ValueError):
                self.store.prepare_start(self.cid)
            with self.assertRaises(ValueError):
                self.store.edit_group(self.cid, self.gid, {'replace': True})
            # Losing access is not evidence of successful deletion.
            self.gateway.delete_group.side_effect = ChannelPrivateError(request=None)
            self.assertEqual(self.delete().status_code, 400)
            self.assertEqual(len(self.store.groups(self.cid)), 1)
            # A new, explicitly confirmed attempt can succeed if Telegram allows it.
            self.gateway.delete_group.side_effect = self.delete_group
            self.assertEqual(self.delete().status_code, 200)

    def test_unknown_ownership_prevents_deletion(self):
        self.store.begin_ownership(self.gid, 'new_owner', 123, 456)
        self.store.finish_ownership(self.gid, 'unknown')
        with patch('group_campaigns.TelegramCampaignGateway') as factory:
            self.assertEqual(self.delete().status_code, 400)
            factory.assert_not_called()

    def test_inflight_deletion_blocks_other_actions(self):
        async def deleting(*args):
            other = self.app.test_client()
            with other.session_transaction() as saved:
                saved['username'] = 'alice'
            self.assertEqual(other.post(f'/api/group-campaigns/{self.cid}/start').status_code, 400)
            self.assertEqual(other.post(self.url + '/ownership', json={}).status_code, 400)
            self.assertEqual(other.delete(self.url, json=self.payload).status_code, 400)
            self.assertEqual(other.delete(f'/api/group-campaigns/{self.cid}').status_code, 400)
            await self.delete_group(*args)
        self.gateway.delete_group.side_effect = deleting
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.delete().status_code, 200)


if __name__ == '__main__':
    unittest.main()
