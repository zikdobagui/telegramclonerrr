import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from automation_manager import AutomationManager


class TaskQueueConcurrencyTests(unittest.TestCase):
    def test_creation_while_active_worker_saves(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = AutomationManager(directory)
            active = worker.add_group_task('active', 100)
            active['status'] = 'active'
            worker.save_config()
            creator = AutomationManager(directory)
            barrier = threading.Barrier(2)

            def save_progress():
                barrier.wait()
                for count in range(20):
                    active['total_added'] = count
                    worker.save_config()

            def create_tasks():
                barrier.wait()
                return [creator.add_group_task(f'queued-{i}', 100)['id'] for i in range(20)]

            with ThreadPoolExecutor(max_workers=2) as pool:
                progress = pool.submit(save_progress)
                creation = pool.submit(create_tasks)
                ids = creation.result(timeout=30)
                progress.result(timeout=30)
            saved = AutomationManager(directory).config['groups']
            self.assertEqual(len(saved), 21)
            self.assertEqual({task['id'] for task in saved}, {active['id'], *ids})
            self.assertEqual(saved[0]['status'], 'active')

    def test_stale_creators_allocate_unique_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            managers = [AutomationManager(directory) for _ in range(8)]
            with ThreadPoolExecutor(max_workers=8) as pool:
                ids = list(pool.map(lambda manager: manager.add_group_task('queued', 10)['id'], managers))
            self.assertEqual(len(set(ids)), 8)
            self.assertEqual(len(AutomationManager(directory).config['groups']), 8)

    def test_delete_preserves_new_tasks_and_stale_save_cannot_restore_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            stale = AutomationManager(directory)
            task = stale.add_group_task('old', 10)
            fresh = AutomationManager(directory)
            new_task = fresh.add_group_task('new', 10)
            self.assertTrue(fresh.delete_task(task['id']))
            stale.save_config()
            saved = AutomationManager(directory).config['groups']
            self.assertEqual([item['id'] for item in saved], [new_task['id']])


if __name__ == '__main__':
    unittest.main()
