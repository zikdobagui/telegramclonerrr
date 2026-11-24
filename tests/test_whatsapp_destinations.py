import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from whatsapp_bridge import NeonizeDevice, WhatsAppError, WhatsAppService

GROUP = '120363000001@g.us'
OTHER = '120363000002@g.us'


class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = WhatsAppService(lambda name: {'data_dir': str(Path(self.temp.name) / name)}, lambda: [])
        self.device = NeonizeDevice('alice', self.service.directory('alice'), Mock())
        self.device.state = 'connected'
        self.device.joined_groups = Mock(return_value=[{'id': GROUP, 'name': 'Cliente'}])
        self.service.devices['alice'] = self.device

    def test_valid_editor_selection_survives_missing_server_cache(self):
        self.assertEqual(self.service.validate_destinations('alice', [GROUP]), [GROUP])
        self.device.joined_groups.assert_called_once()
        self.assertEqual(self.service.settings('alice')['groups'][0]['id'], GROUP)
        self.assertEqual(self.service.validate_destinations('alice', [GROUP]), [GROUP])
        self.device.joined_groups.assert_called_once()

    def test_refresh_keeps_all_selected_destinations_and_deduplicates(self):
        self.device.joined_groups.return_value.append({'id': OTHER, 'name': 'Outro'})
        self.assertEqual(self.service.validate_destinations('alice', [GROUP, OTHER, GROUP]), [GROUP, OTHER])

    def test_foreign_group_remains_rejected_after_authoritative_refresh(self):
        with self.assertRaisesRegex(WhatsAppError, 'não pertence'):
            self.service.validate_destinations('alice', [OTHER])
        with self.assertRaises(WhatsAppError):
            self.service.validate_destinations('bob', [GROUP])

    def test_old_account_cache_cannot_authorize_new_account(self):
        self.service.save_settings('alice', groups=[{'id': OTHER}], groups_generation='old', auth_generation='new')
        with self.assertRaises(WhatsAppError):
            self.service.validate_destinations('alice', [OTHER])

    def test_session_change_during_group_request_cannot_restore_old_cache(self):
        def switched():
            self.service.save_settings('alice', auth_generation='new', groups=[])
            return [{'id': GROUP}]
        self.device.joined_groups.side_effect = switched
        with self.assertRaisesRegex(WhatsAppError, 'conexão.*mudou'):
            self.service.groups('alice')
        self.assertEqual(self.service.settings('alice')['groups'], [])

    def test_connection_failure_does_not_accept_unverified_selection(self):
        self.device.joined_groups.side_effect = ConnectionError('offline')
        with self.assertRaisesRegex(WhatsAppError, 'Não foi possível confirmar'):
            self.service.validate_destinations('alice', [GROUP])

    def test_empty_selection_never_requires_whatsapp(self):
        self.assertEqual(self.service.validate_destinations('bob', []), [])

    def test_replaced_device_callback_cannot_clear_current_group_list(self):
        self.service.start = Mock()
        devices = []
        def factory(name, directory, disable):
            device = NeonizeDevice(name, directory, disable)
            device.launch = Mock()
            devices.append(device)
            return device
        self.service.devices.clear()
        self.service.factory = factory
        self.service.connect('alice')
        self.service.connect('alice')
        self.service.save_settings('alice', groups=[{'id': GROUP}])
        devices[0].on_disable()
        self.assertEqual(self.service.settings('alice')['groups'], [{'id': GROUP}])


if __name__ == '__main__':
    unittest.main()
