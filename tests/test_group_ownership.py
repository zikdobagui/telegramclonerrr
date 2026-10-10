"""Ownership transfer checks; all Telegram requests are mocked."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from flask import Flask
from telethon.errors import PasswordHashInvalidError, PasswordTooFreshError
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator, ChatAdminRights, User

from group_campaigns import CampaignStore, TelegramCampaignGateway, register_campaign_routes, ownership_error


class OwnershipGatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.gateway = TelegramCampaignGateway({}, {}, ())
        self.owner = ChannelParticipantCreator(1, ChatAdminRights())
        self.admin = ChannelParticipantAdmin(2, 1, None, ChatAdminRights())
        self.client = AsyncMock()
        self.client.get_entity.return_value = User(2, access_hash=123)
        self.gateway.peer = AsyncMock(return_value=(self.client, 'peer'))

    async def test_transfer_uses_creator_and_srp_and_records_before_sending(self):
        password_info = SimpleNamespace(has_password=True)
        self.client.side_effect = [SimpleNamespace(participant=self.owner), SimpleNamespace(participant=self.admin), password_info, SimpleNamespace()]
        recorded = Mock(side_effect=lambda *_: self.assertEqual(self.client.await_count, 3))
        with patch('telethon.password.compute_check', return_value='srp-proof') as compute:
            await self.gateway.transfer_ownership({'creator': 'owner.session'}, 'new_owner', 'secret', recorded)
        self.gateway.peer.assert_awaited_once_with({'creator': 'owner.session'}, 'owner.session')
        compute.assert_called_once_with(password_info, 'secret')
        recorded.assert_called_once_with(2, 123)
        request = self.client.await_args.args[0]
        self.assertEqual(request.user_id.user_id, 2)
        self.assertEqual(request.password, 'srp-proof')

    async def test_rejects_non_owner_before_transfer(self):
        self.client.return_value = SimpleNamespace(participant=self.admin)
        with self.assertRaisesRegex(ValueError, 'não é mais dona'):
            await self.gateway.transfer_ownership({'creator': 'owner'}, 'new_owner', 'secret', Mock())
        self.assertEqual(self.client.await_count, 1)

    async def test_rejects_bot_and_non_admin(self):
        self.client.return_value = SimpleNamespace(participant=self.owner)
        self.client.get_entity.return_value = User(2, access_hash=123, bot=True)
        with self.assertRaisesRegex(ValueError, 'não um bot'):
            await self.gateway.transfer_ownership({'creator': 'owner'}, 'new_owner', 'secret', Mock())
        self.client.get_entity.return_value = User(2, access_hash=123)
        self.client.side_effect = [SimpleNamespace(participant=self.owner), SimpleNamespace(participant=object())]
        with self.assertRaisesRegex(ValueError, 'administrador'):
            await self.gateway.transfer_ownership({'creator': 'owner'}, 'new_owner', 'secret', Mock())

    async def test_check_queries_saved_user_id_without_transferring(self):
        transfer = {'user_id': '2', 'access_hash': '123'}
        self.client.return_value = SimpleNamespace(participant=ChannelParticipantCreator(2, ChatAdminRights()))
        self.assertEqual(await self.gateway.check_ownership({'creator': 'owner'}, transfer), 'confirmed')
        self.assertEqual(self.client.await_args.args[0].participant.user_id, 2)
        self.client.side_effect = [SimpleNamespace(participant=self.admin), SimpleNamespace(participant=self.owner)]
        self.assertEqual(await self.gateway.check_ownership({'creator': 'owner'}, transfer), 'failed')
        self.client.get_entity.assert_not_awaited()


class OwnershipApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Flask(__name__)
        self.app.secret_key = 'test'
        from functools import wraps
        from flask import session

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
        with self.client.session_transaction() as saved_session:
            saved_session['username'] = 'alice'
        self.cid = self.client.post('/api/group-campaigns', json={'name': 'Task', 'count': 1, 'sessions': ['owner.session']}).json['id']
        self.store = CampaignStore(str(Path(self.temp.name) / 'alice'))
        self.gid = self.store.groups(self.cid)[0]['id']
        self.store.group_update(self.gid, status='ready', channel_id='10', access_hash='20', creator='owner.session')
        self.url = f'/api/group-campaigns/{self.cid}/groups/{self.gid}/ownership'
        self.payload = {'username': 'new_owner', 'password': 'test-secret-never-save', 'confirmed': True}
        self.gateway = SimpleNamespace(transfer_ownership=AsyncMock(side_effect=self.transfer), check_ownership=AsyncMock(return_value='confirmed'), close=AsyncMock())

    async def transfer(self, group, username, password, before_send):
        before_send(2, 123)

    def post(self, **changes):
        return self.client.post(self.url, json={**self.payload, **changes})

    def test_confirmed_persists_without_password_and_prevents_duplicate(self):
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            response = self.post()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'confirmed')
            self.assertEqual(self.post().status_code, 400)
        self.gateway.transfer_ownership.assert_awaited_once()
        self.gateway.close.assert_awaited_once()
        self.assertEqual(self.store.groups(self.cid)[0]['creator'], 'owner.session')
        snapshot = json.dumps(self.store.snapshot())
        self.assertNotIn(self.payload['password'], snapshot)
        self.assertNotIn('access_hash', json.dumps(self.store.groups(self.cid)[0]['ownership']))
        with self.store.db() as conn:
            self.assertNotIn(self.payload['password'], '\n'.join(conn.iterdump()))
        self.assertEqual(self.store.get(self.cid)['status'], 'paused')
        self.set_lock.assert_called_with('group_campaign', False, username='alice')
        self.assertEqual(self.client.delete(f'/api/group-campaigns/{self.cid}').status_code, 200)

    def test_requires_confirmation_paused_task_and_account_isolation(self):
        with patch('group_campaigns.TelegramCampaignGateway') as factory:
            self.assertEqual(self.post(confirmed=False).status_code, 400)
            self.assertEqual(self.post(password='').status_code, 400)
            self.store.state(self.cid, 'running')
            self.assertEqual(self.post().status_code, 400)
            self.store.state(self.cid, 'paused')
            with self.client.session_transaction() as session:
                session['username'] = 'bob'
            self.assertEqual(self.post().status_code, 400)
            with self.client.session_transaction() as session:
                session.clear()
            self.assertEqual(self.post().status_code, 401)
            factory.assert_not_called()

    def test_uncertain_result_is_not_retried_and_can_be_checked(self):
        async def timeout(*args):
            await self.transfer(*args)
            raise TimeoutError('response lost')
        self.gateway.transfer_ownership.side_effect = timeout
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.post().status_code, 400)
            self.assertEqual(self.store.ownership(self.gid)['status'], 'unknown')
            self.assertEqual(self.post().status_code, 400)
            response = self.client.post(self.url + '/check', json={})
            self.assertEqual(response.json['status'], 'confirmed')
        self.gateway.transfer_ownership.assert_awaited_once()
        self.assertEqual(self.store.ownership(self.gid)['status'], 'confirmed')

    def test_password_error_allows_manual_retry_and_releases_lock(self):
        async def invalid(*args):
            await self.transfer(*args)
            raise PasswordHashInvalidError(request=None)
        self.gateway.transfer_ownership.side_effect = invalid
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            response = self.post()
            self.assertIn('incorreta', response.json['error'])
            self.assertEqual(self.store.ownership(self.gid)['status'], 'failed')
            self.gateway.transfer_ownership.side_effect = self.transfer
            self.assertEqual(self.post().status_code, 200)

    def test_pending_survives_restart_as_unknown(self):
        self.store.begin_ownership(self.gid, 'new_owner', 2, 123)
        self.store.recover()
        self.assertEqual(self.store.ownership(self.gid)['status'], 'unknown')
        with self.assertRaises(ValueError):
            self.store.begin_ownership(self.gid, 'someone_else', 3, 456)

    def test_inflight_transfer_blocks_start_edit_and_other_transfer(self):
        async def transfer(*args):
            other = self.app.test_client()
            with other.session_transaction() as session:
                session['username'] = 'alice'
            self.assertEqual(other.post(f'/api/group-campaigns/{self.cid}/start').status_code, 400)
            self.assertEqual(other.delete(f'/api/group-campaigns/{self.cid}').status_code, 400)
            self.assertEqual(other.put(f'/api/group-campaigns/{self.cid}/groups/{self.gid}', json={'replace': True}).status_code, 400)
            self.assertEqual(other.post(self.url, json=self.payload).status_code, 400)
            await self.transfer(*args)
        self.gateway.transfer_ownership.side_effect = transfer
        with patch('group_campaigns.TelegramCampaignGateway', return_value=self.gateway):
            self.assertEqual(self.post().status_code, 200)

    def test_friendly_wait_and_unexpected_errors_do_not_echo_secrets(self):
        self.assertIn('123 segundos', ownership_error(PasswordTooFreshError(request=None, capture=123)))
        self.assertNotIn('secret', ownership_error(ValueError('secret')))


if __name__ == '__main__':
    unittest.main()
