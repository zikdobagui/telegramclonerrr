import ast
import unittest
from pathlib import Path


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
