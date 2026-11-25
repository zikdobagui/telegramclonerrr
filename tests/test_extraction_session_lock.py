import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock


class ExtractionSessionLockTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'create_session_lock_state', 'check_session_lock', 'set_session_lock'}]
        self.state = {}
        self.namespace = {'get_user_lock_state': lambda username=None: self.state}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'app.py', 'exec'), self.namespace)
        self.state.update(self.namespace['create_session_lock_state']())
        self.state.update(group_campaign=True, group_campaign_sessions={'busy.session'})

    def check(self, **kwargs):
        return self.namespace['check_session_lock']('extraction', **kwargs)[0]

    def test_free_session_can_extract(self):
        self.assertTrue(self.check(session_name='free.session'))

    def test_campaign_session_cannot_extract(self):
        self.assertFalse(self.check(session_name='busy.session'))

    def test_other_extraction_still_blocks(self):
        self.state['extraction'] = True
        self.assertFalse(self.check(session_name='free.session'))

    def test_unknown_campaign_sessions_still_block(self):
        self.state.pop('group_campaign_sessions')
        self.assertFalse(self.check(session_name='free.session'))

    def test_unlock_clears_session_reservations(self):
        self.namespace['set_session_lock']('group_campaign', False)
        self.assertNotIn('group_campaign_sessions', self.state)
        self.assertTrue(self.check(session_name='busy.session'))


class VisibilitySessionLockTests(unittest.TestCase):
    setUp = ExtractionSessionLockTests.setUp

    def check(self, name):
        return self.namespace['check_session_lock']('group_visibility', username='alice', session_name=name)[0]

    def test_only_campaign_accounts_are_blocked(self):
        self.assertFalse(self.check('busy.session'))
        self.assertTrue(self.check('free.session'))

    def test_known_operations_only_block_their_selected_accounts(self):
        for kind in ('warming', 'extraction', 'addition', 'group_factory'):
            with self.subTest(kind=kind):
                self.state[kind] = True
                self.state[kind + '_sessions'] = {'other.session'}
                self.assertFalse(self.check('other.session'))
                self.assertTrue(self.check('free.session'))
                self.namespace['set_session_lock'](kind, False)
                self.assertNotIn(kind + '_sessions', self.state)

    def test_session_names_are_saved_and_cleared(self):
        self.namespace['set_session_lock']('extraction', True, session_names=['extract.session'])
        self.assertFalse(self.check('extract.session'))
        self.assertTrue(self.check('free.session'))
        self.namespace['set_session_lock']('extraction', False)
        self.assertTrue(self.check('extract.session'))

    def test_availability_keeps_250_free_sessions_alongside_146_used(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'visibility_session_availability')
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'app.py', 'exec'), self.namespace)
        self.namespace['get_automation_manager_instance'] = lambda username: SimpleNamespace(get_reserved_task_sessions=lambda: [])
        sessions = [{'session_name': f'account-{index}.session'} for index in range(396)]
        self.state['group_campaign_sessions'] = {info['session_name'] for info in sessions[:146]}
        reasons = self.namespace['visibility_session_availability']('alice', sessions)
        self.assertEqual(sum(not reason for reason in reasons.values()), 250)
        self.assertEqual(sum(bool(reason) for reason in reasons.values()), 146)
        self.state['active_tasks'].add(1)
        self.assertTrue(self.check(sessions[-1]['session_name']))
        self.namespace['get_automation_manager_instance'] = lambda username: SimpleNamespace(get_reserved_task_sessions=lambda: [200])
        reasons = self.namespace['visibility_session_availability']('alice', sessions)
        self.assertEqual(sum(not reason for reason in reasons.values()), 249)
        self.assertIn('Reservada', reasons[sessions[200]['session_name']])


class ExtractionStartTests(unittest.TestCase):
    def setUp(self):
        ExtractionSessionLockTests.setUp(self)
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8'))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'start_extraction_worker')
        self.thread = Mock()
        self.namespace.update(threading=SimpleNamespace(Thread=self.thread), extraction_start_guard=threading.Lock())
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'app.py', 'exec'), self.namespace)

    def test_concurrent_requests_reserve_before_thread_start(self):
        def start(_):
            try:
                self.namespace['start_extraction_worker'](lambda: None, 'alice', 'free.session')
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(start, range(2)))
        self.assertEqual(sum(results), 1)
        self.thread.assert_called_once()
        self.assertTrue(self.state['extraction'])
        self.assertEqual(self.state['extraction_sessions'], {'free.session'})

    def test_thread_start_failure_releases_reservation(self):
        self.thread.return_value.start.side_effect = RuntimeError('cannot start')
        with self.assertRaises(RuntimeError):
            self.namespace['start_extraction_worker'](lambda: None, 'alice', 'free.session')
        self.assertFalse(self.state['extraction'])
        self.assertNotIn('extraction_sessions', self.state)
