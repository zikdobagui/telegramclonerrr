import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from whatsapp_bridge import WhatsAppService, NeonizeDevice, WhatsAppError


class DisconnectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = WhatsAppService(lambda name: {'data_dir': str(Path(self.temp.name) / name)}, lambda: [])

    def finish_unlink_inline(self):
        def thread(*args, target, **kwargs):
            return Mock(start=target)
        return patch('whatsapp_bridge.threading.Thread', side_effect=thread)

    def test_unlinks_removes_only_auth_and_next_connection_gets_new_qr(self):
        directory = self.service.directory('alice')
        directory.mkdir(parents=True)
        for suffix in ('', '-wal', '-shm', '-journal'):
            (directory / ('auth.sqlite' + suffix)).write_text('old credentials')
        other = self.service.directory('bob')
        other.mkdir(parents=True)
        (other / 'auth.sqlite').write_text('other account')
        self.service.store('alice').enqueue('p1', 'clone1', ['120363000001@g.us'], 'history')
        old = NeonizeDevice('alice', directory, Mock())
        old.client = Mock()
        old.state = 'connected'
        old.receive_qr(b'old-qr')
        self.service.devices['alice'] = old
        self.service.save_settings('alice', enabled=True, groups=['old-group'])
        with self.finish_unlink_inline():
            self.service.disconnect('alice')
        old.client.logout.assert_called_once()
        old.client.stop.assert_called_once()
        self.assertFalse((directory / 'auth.sqlite').exists())
        self.assertTrue((directory / 'outbox.sqlite').exists())
        self.assertTrue((other / 'auth.sqlite').exists())
        self.assertFalse(self.service.settings('alice')['enabled'])
        self.assertEqual(self.service.settings('alice')['groups'], [])
        self.assertIsNone(old.snapshot()['qr'])
        new = NeonizeDevice('alice', directory, Mock())
        self.assertNotEqual(new.auth_path, old.auth_path)
        self.assertFalse(new.auth_path.exists())
        new.receive_qr(b'new-qr')
        self.assertNotEqual(new.snapshot()['qr_revision'], old.qr_digest)
        self.assertTrue(new.snapshot()['qr_available'])

    def test_offline_logout_still_invalidates_pairing(self):
        directory = self.service.directory('alice')
        directory.mkdir(parents=True)
        old = NeonizeDevice('alice', directory, Mock())
        old.client = Mock()
        old.client.logout.side_effect = ConnectionError('offline')
        self.service.devices['alice'] = old
        with self.finish_unlink_inline():
            self.service.disconnect('alice')
        self.assertEqual(old.state, 'disconnected')
        self.assertNotEqual(NeonizeDevice('alice', directory, Mock()).auth_path, old.auth_path)

    def test_connect_cannot_race_an_unlink_in_progress(self):
        old = NeonizeDevice('alice', self.service.directory('alice'), Mock())
        old.state = 'disconnecting'
        self.service.devices['alice'] = old
        with self.assertRaises(WhatsAppError):
            self.service.connect('alice')

    def test_late_old_device_callback_cannot_disable_new_generation(self):
        made = []
        def factory(name, directory, disable):
            device = NeonizeDevice(name, directory, disable)
            device.launch = Mock()
            made.append(device)
            return device
        self.service.factory = factory
        self.service.start = Mock()
        self.service.connect('alice')
        with self.finish_unlink_inline():
            self.service.disconnect('alice')
        self.service.connect('alice')
        made[0].on_disable()
        self.assertTrue(self.service.settings('alice')['enabled'])
        self.assertNotEqual(made[0].auth_path, made[1].auth_path)


if __name__ == '__main__':
    unittest.main()
