"""No pairing, network connections, or real Telegram/WhatsApp sends in these tests."""
import asyncio
import ast
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, AsyncMock, patch

from flask import Flask, session
from whatsapp_bridge import Outbox, WhatsAppService, WhatsAppError, NeonizeDevice, register_whatsapp_routes
from channel_cloner import ChannelCloner

GROUP = '120363000001@g.us'


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.outbox=Outbox(self.temp.name)

    def test_duplicate_event_and_group_have_only_one_delivery(self):
        for _ in range(2):self.outbox.enqueue('post1','clone1',[GROUP],'Hello')
        row=self.outbox.claim();self.assertEqual(row['text'],'Hello')
        self.assertIsNone(self.outbox.claim())

    def test_claim_is_atomic_across_threads(self):
        self.outbox.enqueue('post1','clone1',[GROUP],'Hello')
        with ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:self.outbox.claim(),range(4)))
        self.assertEqual(sum(row is not None for row in results),1)

    def test_restart_does_not_retry_ambiguous_send(self):
        self.outbox.enqueue('post1','clone1',[GROUP],'Hello');self.outbox.claim()
        restored=Outbox(self.temp.name);restored.recover()
        self.assertIsNone(restored.claim());self.assertEqual(restored.summary()['counts']['unknown'],1)

    def test_pending_survives_restart(self):
        self.outbox.enqueue('post1','clone1',[GROUP],'Hello')
        restored=Outbox(self.temp.name);restored.recover()
        self.assertEqual(restored.claim()['text'],'Hello')

    def test_shared_media_retained_until_last_group_is_finished(self):
        media=Path(self.temp.name)/'media'/'test.bin';media.write_bytes(b'test')
        self.outbox.enqueue('post1','clone1',[GROUP,'120363000002@g.us'],'Caption',str(media),'image')
        first=self.outbox.claim();self.outbox.finish(first['id'],'sent','ok')
        self.assertTrue(media.exists())
        second=self.outbox.claim();self.outbox.finish(second['id'],'sent','ok')
        self.assertFalse(media.exists())


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.service=WhatsAppService(lambda u:{'data_dir':str(self.root/u)},lambda:[])
        self.service.start=Mock() # Never launch production supervisor in tests.
        self.service.save_settings('alice',groups=[{'id':GROUP,'name':'Own group'}])

    async def test_text_enqueue_is_scoped_and_idempotent(self):
        message=SimpleNamespace(id=4,chat_id=123,photo=None,document=None)
        for _ in range(2):await self.service.enqueue_clone('alice','clone1',message,'**Offer**',[GROUP],AsyncMock())
        self.assertEqual(self.service.store('alice').summary()['counts']['pending'],1)
        self.assertEqual(self.service.store('alice').claim()['text'],'*Offer*')
        self.assertEqual(self.service.store('bob').summary()['counts'],{})

    async def test_foreign_group_and_non_group_rejected(self):
        with self.assertRaises(WhatsAppError):self.service.validate_destinations('bob',[GROUP])
        with self.assertRaises(WhatsAppError):self.service.validate_destinations('alice',['123@s.whatsapp.net'])
        with self.assertRaises(WhatsAppError):self.service.validate_destinations('alice','not a list')
        self.assertEqual(self.service.validate_destinations('alice',[]),[])

    async def test_photo_is_persisted_before_queue(self):
        message=SimpleNamespace(id=4,chat_id=123,photo=True,document=None,file=SimpleNamespace(size=4,mime_type='image/jpeg',name='photo.jpg'))
        async def download(message,file):Path(file).write_bytes(b'test');return file
        telegram=SimpleNamespace(download_media=download)
        await self.service.enqueue_clone('alice','clone1',message,'Caption',[GROUP],telegram)
        row=self.service.store('alice').claim()
        self.assertEqual(row['kind'],'image');self.assertEqual(Path(row['media']).read_bytes(),b'test')

    async def test_oversized_media_never_downloaded(self):
        message=SimpleNamespace(id=4,chat_id=123,photo=True,document=None,file=SimpleNamespace(size=20*1024*1024))
        telegram=AsyncMock()
        with self.assertRaises(WhatsAppError):await self.service.enqueue_clone('alice','clone1',message,'Caption',[GROUP],telegram)
        telegram.download_media.assert_not_awaited()

    async def test_send_confirmed_and_ambiguous_never_automatically_retried(self):
        store=self.service.store('alice');store.enqueue('p1','clone1',[GROUP],'Hello')
        device=SimpleNamespace(state='connected',send_guard=threading.Lock(),last_send=0,send=Mock(return_value='wa-id'))
        self.service.send_next('alice',device);self.assertEqual(store.summary()['counts']['sent'],1)
        store.enqueue('p2','clone1',[GROUP],'Next');device.last_send=0;device.send.side_effect=TimeoutError()
        self.service.send_next('alice',device);self.assertEqual(store.summary()['counts']['unknown'],1)
        device.last_send=0;self.service.send_next('alice',device)
        self.assertEqual(device.send.call_count,2)

    async def test_offline_does_not_claim_messages(self):
        store=self.service.store('alice');store.enqueue('p1','clone1',[GROUP],'Hello')
        device=SimpleNamespace(state='reconnecting',send_guard=threading.Lock(),last_send=0)
        self.service.send_next('alice',device)
        self.assertEqual(store.summary()['counts']['pending'],1)

    async def test_device_limit_does_not_enable_extra_user(self):
        alive=SimpleNamespace(thread=SimpleNamespace(is_alive=lambda:True),stopping=False)
        self.service.devices['alice']=alive;self.service.max_devices=1
        with self.assertRaises(WhatsAppError):self.service.connect('bob')
        self.assertFalse(self.service.settings('bob')['enabled'])

    async def test_live_config_is_used_and_whatsapp_failure_does_not_resend_telegram(self):
        cloner=ChannelCloner(123,'hash','phone','unused')
        cloner.client=AsyncMock();cloner.whatsapp_sink=AsyncMock(side_effect=WhatsAppError('offline'))
        cloner.whatsapp_error_sink=Mock()
        config={'whatsapp_groups':[GROUP],'prefix':'Prefix'}
        message=SimpleNamespace(id=1,text='Post',message='Post',media=None)
        self.assertTrue(await cloner.clone_message(message,'@target',config,'clone1'))
        self.assertFalse(await cloner.clone_message(message,'@target',config,'clone1'))
        cloner.client.send_message.assert_awaited_once()
        cloner.whatsapp_error_sink.assert_called_once()

    async def test_latest_saved_whatsapp_destinations_can_be_removed_live(self):
        from data_store import atomic_write_json
        cloner=ChannelCloner(123,'hash','phone','unused')
        cloner.clones_file=str(self.root/'clones.json')
        atomic_write_json(cloner.clones_file,{'clones':[{'id':'clone1','whatsapp_groups':[]}]})
        self.assertEqual(cloner.get_latest_clone_config('clone1',{'whatsapp_groups':[GROUP]})['whatsapp_groups'],[])


class DeviceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)

    def test_neonize_qr_callback_is_raw_data_and_registers_before_connect(self):
        from neonize.events import ConnectedEv
        handlers={};snapshots=[]
        client=Mock()
        def register(event):
            def decorate(fn):handlers[event]=fn
            return decorate
        client.event.side_effect=register
        def qr(fn):client.qr_handler=fn
        client.qr.side_effect=qr
        device=NeonizeDevice('alice',self.temp.name,Mock())
        def connect():
            client.qr_handler(client,b'neonize-test-pairing-data')
            snapshots.append(device.snapshot())
            handlers[ConnectedEv](client,None)
            snapshots.append(device.snapshot())
        client.connect.side_effect=connect
        with patch('neonize.client.NewClient',return_value=client):device.run()
        self.assertTrue(snapshots[0]['qr'].startswith('data:image/png;base64,iVBOR'))
        self.assertEqual(snapshots[0]['status'],'qr')
        self.assertEqual(snapshots[1]['status'],'connected');self.assertIsNone(snapshots[1]['qr'])

    def test_media_send_uses_group_jid_and_caption(self):
        device=NeonizeDevice('alice',self.temp.name,Mock());device.state='connected';device.client=Mock()
        device.client.send_image.return_value=SimpleNamespace(ID='receipt')
        receipt=device.send({'group_jid':GROUP,'kind':'image','media':'test.jpg','text':'Caption'})
        self.assertEqual(receipt,'receipt')
        args,kwargs=device.client.send_image.call_args
        self.assertEqual(args[0].Server,'g.us');self.assertEqual(kwargs['caption'],'Caption')

    def test_group_metadata_matches_pinned_library_contract(self):
        device=NeonizeDevice('alice',self.temp.name,Mock());device.state='connected';device.client=Mock()
        device.client.get_joined_groups.return_value=[SimpleNamespace(JID=SimpleNamespace(User='120363000001',Server='g.us'),GroupName=SimpleNamespace(Name='Own group'),Participants=[1,2],GroupAnnounce=SimpleNamespace(IsAnnounce=True))]
        self.assertEqual(device.joined_groups(),[{'id':GROUP,'name':'Own group','members':2,'admin_only':True}])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__);self.app.secret_key='test';self.service=Mock()
        def auth(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                if 'username' not in session:return {'success':False},401
                return fn(*args,**kwargs)
            return wrapped
        register_whatsapp_routes(self.app,auth,self.service)
        self.client=self.app.test_client()
        with self.client.session_transaction() as s:s['username']='alice'

    def test_qr_status_is_private_and_requires_authentication(self):
        self.service.status.return_value={'status':'qr','qr':'secret-qr'}
        response=self.client.get('/api/whatsapp');self.assertIn('no-store',response.headers['Cache-Control'])
        self.service.status.assert_called_once_with('alice')
        self.assertEqual(self.app.test_client().get('/api/whatsapp').status_code,401)

    def test_actions_cannot_choose_another_username(self):
        self.client.post('/api/whatsapp/connect',json={'username':'bob'})
        self.service.connect.assert_called_once_with('alice')
        self.client.post('/api/whatsapp/disconnect')
        self.service.disconnect.assert_called_once_with('alice')

    def test_groups_scoped_and_offline_error(self):
        self.service.groups.side_effect=WhatsAppError('Connect first')
        self.assertEqual(self.client.get('/api/whatsapp/groups').status_code,409)
        self.service.groups.assert_called_once_with('alice')


class CloningRouteTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__);self.app.secret_key='test'
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=WhatsAppService(lambda u:{'data_dir':str(Path(self.temp.name)/u)},lambda:[])
        self.service.save_settings('alice',groups=[{'id':GROUP,'name':'Own group'}])
        self.saved=[]
        def add(config):config['id']='clone1';config['active']=False;self.saved.append(config);return 'clone1'
        manager=SimpleNamespace(load_clones=lambda:self.saved,add_clone=add,save_clones=lambda rows:None)
        def auth(fn):return fn
        from flask import request,jsonify
        source=ast.parse(Path('app.py').read_text(encoding='utf-8'))
        functions=[node for node in source.body if isinstance(node,ast.FunctionDef) and node.name in ('manage_clones','clone_operations')]
        env={'app':self.app,'login_required':auth,'request':request,'jsonify':jsonify,'session':session,
             'clone_manager':manager,'whatsapp_service':self.service,'WhatsAppError':WhatsAppError}
        exec(compile(ast.Module(body=functions,type_ignores=[]),'cloning-routes','exec'),env)
        self.client=self.app.test_client()
        with self.client.session_transaction() as s:s['username']='alice'

    def test_create_and_edit_preserve_or_remove_whatsapp_destinations(self):
        payload={'name':'Offer','session_name':'session','source_channel':'@source','dest_channel':'@dest','whatsapp_groups':[GROUP]}
        self.assertEqual(self.client.post('/api/clones',json=payload).status_code,200)
        self.assertEqual(self.saved[0]['whatsapp_groups'],[GROUP])
        self.assertEqual(self.client.put('/api/clones/clone1',json={'name':'Updated'}).status_code,200)
        self.assertEqual(self.saved[0]['whatsapp_groups'],[GROUP])
        self.assertEqual(self.client.put('/api/clones/clone1',json={'whatsapp_groups':[]}).status_code,200)
        self.assertEqual(self.saved[0]['whatsapp_groups'],[])

    def test_foreign_group_cannot_be_saved_in_clone(self):
        response=self.client.post('/api/clones',json={'whatsapp_groups':['120363999999@g.us']})
        self.assertEqual(response.status_code,400);self.assertEqual(self.saved,[])


if __name__=='__main__':unittest.main()
