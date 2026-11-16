"""Group visibility checks; never connects to Telegram or reads real sessions."""
import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from flask import Flask, session
from telethon import errors, types, functions
from group_visibility import parse_groups, inspect_group, classify_error, register_visibility_routes, visible_groups_text


class ParserTests(unittest.TestCase):
    def test_escaped_export_and_duplicate_ids_use_links(self):
        groups, invalid, duplicates = parse_groups(
            '(1) | 2147483647 | Grupo | Membros: 2113 | https\\://t.me/bugsshopeebrasil\\\n'
            '(2) | 2147483647 | Outro | https://t.me/OutroGrupo\n'
            '@BUGSSHOPEEBRASIL\nnot a link\nhttps://t.me/+PrivateHash')
        self.assertEqual([g['token'] for g in groups], ['bugsshopeebrasil','OutroGrupo','+PrivateHash'])
        self.assertEqual(invalid, [4])
        self.assertEqual(duplicates, 1)
        self.assertTrue(groups[-1]['private'])

    def test_invalid_inputs_and_reserved_links(self):
        for text in (None, [], 'a' * 1_000_001):
            with self.assertRaises(ValueError): parse_groups(text)
        self.assertEqual(len(parse_groups('https://t.me/share\n2147483647')[0]), 0)


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock()
        self.group = parse_groups('https://t.me/example_group')[0][0]
        self.entity = types.Channel(id=123, title='Example', photo=types.ChatPhotoEmpty(), date=datetime.now(timezone.utc), megagroup=True)
        self.client.get_entity.return_value = self.entity

    async def test_hidden_group_does_not_probe_members_even_for_admin(self):
        self.client.return_value = SimpleNamespace(full_chat=SimpleNamespace(participants_hidden=True, participants_count=2000))
        result = await inspect_group(self.client, self.group)
        self.assertEqual(result['status'], 'hidden')
        self.assertEqual(self.client.await_count, 1)

    async def test_visible_requires_successful_minimal_participants_query(self):
        self.client.side_effect = [SimpleNamespace(full_chat=SimpleNamespace(participants_hidden=False, participants_count=2000)),SimpleNamespace(participants=[object()])]
        result = await inspect_group(self.client, self.group)
        self.assertEqual(result['status'], 'visible')
        probe = self.client.await_args.args[0]
        self.assertIsInstance(probe, functions.channels.GetParticipantsRequest)
        self.assertEqual(probe.limit, 1)
        self.assertNotIn('participants', result)

    async def test_empty_probe_is_not_visible(self):
        self.client.side_effect = [SimpleNamespace(full_chat=SimpleNamespace(participants_hidden=False)),SimpleNamespace(participants=[])]
        self.assertEqual((await inspect_group(self.client, self.group))['status'], 'inconclusive')

    async def test_permission_denied_is_not_confused_with_visible_admins(self):
        self.client.return_value=SimpleNamespace(full_chat=SimpleNamespace(participants_hidden=False,can_view_participants=False))
        self.assertEqual((await inspect_group(self.client,self.group))['status'],'inaccessible')
        self.assertEqual(self.client.await_count,1)

    async def test_private_invite_is_not_joined(self):
        self.client.return_value = SimpleNamespace()
        group=parse_groups('https://t.me/+PrivateHash')[0][0]
        self.assertEqual((await inspect_group(self.client, group))['status'], 'inaccessible')
        self.assertIsInstance(self.client.await_args.args[0], functions.messages.CheckChatInviteRequest)
        self.assertEqual(self.client.await_count, 1)

    async def test_broadcast_channel_not_classified_as_group(self):
        self.entity.megagroup=False
        self.assertEqual((await inspect_group(self.client, self.group))['status'], 'not_group')
        self.client.assert_not_awaited()

    def test_access_errors_differ_from_hidden_and_flood(self):
        self.assertEqual(classify_error(errors.ChatAdminRequiredError(None))[0], 'inaccessible')
        self.assertEqual(classify_error(errors.FloodWaitError(None, capture=123))[0], 'flood')
        self.assertEqual(classify_error(TimeoutError())[0], 'error')


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.app=Flask(__name__);self.app.secret_key='test'
        self.manager=SimpleNamespace(load_sessions=lambda **_: [{'session_name':'own.session','active':True,'status':'active'}])
        self.locks={}
        def paths(username):
            base=self.root/username
            (base/'sessions').mkdir(parents=True,exist_ok=True)
            (base/'sessions'/'own.session').touch(exist_ok=True)
            return {'data_dir':str(base),'sessions_dir':str(base/'sessions'),'floods_file':str(base/'floods.json')}
        self.paths=paths
        def authenticated(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                if 'username' not in session:return {'success':False},401
                return fn(*args,**kwargs)
            return wrapped
        def check(operation,username):return (not self.locks.get(username,False),'Sessão ocupada')
        def lock(operation,value,username):self.locks[username]=value
        register_visibility_routes(self.app,authenticated,paths,lambda _:self.manager,lambda:(123,'hash'),check,lock)
        self.client=self.app.test_client()
        with self.client.session_transaction() as s:s['username']='alice'

    def payload(self,**changes):
        return dict(groups='https://t.me/example_group',sessions=['own.session'],limit=1,**changes)

    def test_unauthenticated_and_validation(self):
        self.assertEqual(self.app.test_client().get('/api/group-visibility').status_code,401)
        payload=self.payload();payload['sessions']=['../bob/own.session']
        self.assertEqual(self.client.post('/api/group-visibility/start',json=payload).status_code,400)
        payload=self.payload();payload['limit']=True
        self.assertEqual(self.client.post('/api/group-visibility/start',json=payload).status_code,400)
        self.assertEqual(self.client.post('/api/group-visibility/start',json=[]).status_code,400)

    def test_start_locks_and_second_start_rejected_and_cancel(self):
        with patch('group_visibility.threading.Thread') as thread:
            result=self.client.post('/api/group-visibility/start',json=self.payload())
            self.assertEqual(result.status_code,202)
            self.assertTrue(self.locks['alice']);thread.return_value.start.assert_called_once()
            self.assertEqual(self.client.post('/api/group-visibility/start',json=self.payload()).status_code,409)
            self.assertEqual(self.client.post('/api/group-visibility/cancel',json={}).status_code,200)
            self.assertEqual(self.client.get('/api/group-visibility').json['job']['status'],'cancelling')

    def test_accepts_existing_manager_names_without_session_extension(self):
        self.manager.load_sessions=lambda **_: [{'session_name':'own','active':True}]
        payload=self.payload();payload['sessions']=['own']
        with patch('group_visibility.threading.Thread'):
            self.assertEqual(self.client.post('/api/group-visibility/start',json=payload).status_code,202)

    def test_export_is_user_scoped_and_visible_only_and_restart(self):
        base=Path(self.paths('alice')['data_dir'])
        (base/'group_visibility.json').write_text(json.dumps({'status':'running','results':[
            {'status':'visible','original':'old input count','title':'Example Group','members_count':2113,'link':'https://t.me/example_group'},
            {'status':'hidden','original':'HIDDEN LINE','link':'https://t.me/hidden_group'}]}),encoding='utf-8')
        self.assertEqual(self.client.get('/api/group-visibility').json['job']['status'],'interrupted')
        expected='Example Group | Membros: 2113 | https://t.me/example_group'
        self.assertEqual(self.client.get('/api/group-visibility/export').text,expected)
        self.assertEqual(self.client.get('/api/group-visibility').json['job']['visible_text'],expected)
        with self.client.session_transaction() as s:s['username']='bob'
        self.assertIsNone(self.client.get('/api/group-visibility').json['job'])
        self.assertEqual(self.client.get('/api/group-visibility/export').text,'')

    def test_export_preserves_zero_and_does_not_invent_missing_counts(self):
        text=visible_groups_text({'results':[
            {'status':'visible','title':'Zero\nGroup','members_count':0,'link':'https://t.me/zero_group'},
            {'status':'visible','title':'Unknown','link':'https://t.me/unknown_group'},
            {'status':'hidden','title':'Hidden','members_count':99,'link':'https://t.me/hidden_group'}]})
        self.assertEqual(text,'Zero Group | Membros: 0 | https://t.me/zero_group\nUnknown | Membros: não informado | https://t.me/unknown_group')

    def test_preview_normalizes_export(self):
        result=self.client.post('/api/group-visibility/preview',json={'groups':'@Example_group\nhttps://t.me/example_group\ninvalid line'})
        self.assertEqual(result.json['valid_links'],1)
        self.assertEqual(result.json['duplicates'],1)
        self.assertEqual(result.json['invalid_lines'],[3])

    def test_worker_disconnects_unlocks_and_persists_results(self):
        async def inspect(*_):return {'status':'visible','reason':'confirmed'}
        client=AsyncMock();client.is_user_authorized.return_value=True
        with patch('telethon.TelegramClient',return_value=client),patch('group_visibility.inspect_group',side_effect=inspect):
            self.assertEqual(self.client.post('/api/group-visibility/start',json=self.payload()).status_code,202)
            import time
            for _ in range(100):
                result=self.client.get('/api/group-visibility').json['job']
                if result['status']=='completed' and not self.locks['alice']:break
                time.sleep(.01)
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['processed'],1)
            self.assertFalse(self.locks['alice'])
            client.disconnect.assert_awaited_once()

    def test_flood_stops_without_rotating_and_records_wait(self):
        client=AsyncMock();client.is_user_authorized.return_value=True
        payload=self.payload();payload.update(groups='@example_one\n@example_two',limit=2)
        with patch('telethon.TelegramClient',return_value=client),patch('group_visibility.inspect_group',side_effect=errors.FloodWaitError(None,capture=60)) as inspect:
            self.client.post('/api/group-visibility/start',json=payload)
            import time
            for _ in range(100):
                result=self.client.get('/api/group-visibility').json['job']
                if result['status']=='flood' and not self.locks['alice']:break
                time.sleep(.01)
            self.assertEqual(result['status'],'flood');self.assertEqual(result['processed'],1)
            self.assertEqual(inspect.call_count,1)
            self.assertTrue((self.root/'alice'/'floods.json').exists())


if __name__=='__main__':unittest.main()
